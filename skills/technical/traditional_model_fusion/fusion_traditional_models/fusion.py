from __future__ import annotations

import itertools
from dataclasses import asdict
from typing import Dict, List, Tuple

from .types import ModelRun, Signal
from .utils import clamp


DEFAULT_WEIGHTS = {
    "advanced_trend_tracking_system": 0.35,
    "volume_price_momentum_analysis": 0.30,
    "oscillator_check": 0.25,
    "trend_application_dulling_divergence": 0.10,
}


def _signed(direction: str) -> int:
    if direction == "bullish":
        return 1
    if direction == "bearish":
        return -1
    return 0


def _risk_penalty(risk_level: str, needs_review: bool) -> float:
    penalty = 1.0
    if risk_level == "high":
        penalty *= 0.6
    elif risk_level == "medium":
        penalty *= 0.8
    if needs_review:
        penalty *= 0.6
    return penalty


def _agreement_matrix(runs: List[ModelRun]) -> Dict[str, Dict[str, bool]]:
    matrix: Dict[str, Dict[str, bool]] = {}
    for a in runs:
        matrix[a.name] = {}
        for b in runs:
            matrix[a.name][b.name] = (a.signal.get("direction") == b.signal.get("direction"))
    return matrix


def fuse_signals(
    model_signals: Dict[str, Signal],
    *,
    threshold: float = 0.6,
    base_weights: Dict[str, float] | None = None,
) -> Dict[str, object]:
    """
    Fuse four model signals into:
    - fused_signal (Signal JSON)
    - model_signals (with vote/weights)
    - validation_report (agreement/conflicts/gates/thresholds)
    """
    base_weights = dict(DEFAULT_WEIGHTS if base_weights is None else base_weights)

    gates_triggered: List[Dict[str, object]] = []
    conflicts: List[Dict[str, object]] = []

    # Extract for gating decisions.
    trend = model_signals.get("advanced_trend_tracking_system")
    osc = model_signals.get("oscillator_check")

    # Effective weights start as base.
    effective = dict(base_weights)

    # Gate 1: ADX<20 => trend output neutral and should downweight trend contribution.
    if trend:
        trend_meta = trend.get("meta") or {}
        adx_gate = (((trend_meta.get("sub_signals") or {}).get("adx14") or {}).get("gate")) if isinstance(trend_meta, dict) else None
        if adx_gate == "unavailable":
            gates_triggered.append(
                {
                    "gate": "adx_unavailable_no_trend_confirmation",
                    "reason": "趋势模块 ADX 不可用，趋势方向不参与确认",
                    "effective_weight": effective.get("advanced_trend_tracking_system", 0.0),
                }
            )
        if adx_gate == "ranging" or trend.get("direction") == "neutral" and "ADX<20" in (trend.get("reasoning") or ""):
            effective["advanced_trend_tracking_system"] = min(effective.get("advanced_trend_tracking_system", 0.0), 0.2)
            gates_triggered.append(
                {
                    "gate": "adx_ranging_downweight_trend",
                    "reason": "趋势模块判定震荡环境（ADX<20），趋势权重降到<=0.2",
                    "effective_weight": effective["advanced_trend_tracking_system"],
                }
            )

    # Gate 2: oscillator conflicts => force fused neutral/low confidence.
    force_neutral = False
    if osc and isinstance(osc.get("meta"), dict) and bool((osc["meta"]).get("needs_human_review")):
        # Only force neutral when oscillator itself says it has conflicts.
        if any("冲突" in u for u in ((osc["meta"]).get("uncertainties") or [])):
            force_neutral = True
            gates_triggered.append(
                {
                    "gate": "oscillator_conflict_force_neutral",
                    "reason": "震荡类指标多空冲突且 needs_human_review=true，融合层强制 neutral",
                }
            )

    # Vote computation.
    runs: List[ModelRun] = []
    total_vote = 0.0
    for name, sig in model_signals.items():
        base_w = float(base_weights.get(name, 0.0))
        eff_w = float(effective.get(name, base_w))
        direction = sig.get("direction", "neutral")
        confidence = float(sig.get("confidence", 0.0) or 0.0)
        meta = sig.get("meta") if isinstance(sig.get("meta"), dict) else {}
        risk_level = (meta or {}).get("risk_level", "medium")
        needs_review = bool((meta or {}).get("needs_human_review", False))
        adj = confidence * _risk_penalty(str(risk_level), needs_review)
        vote = eff_w * _signed(str(direction)) * adj
        notes: List[str] = []
        if eff_w != base_w:
            notes.append(f"weight gated: {base_w:.2f} -> {eff_w:.2f}")
        if needs_review:
            notes.append("needs_human_review=true (penalty applied)")
        if str(risk_level) in ("high", "medium"):
            notes.append(f"risk_level={risk_level} (penalty applied)")
        runs.append(ModelRun(name=name, signal=sig, base_weight=base_w, effective_weight=eff_w, vote=vote, notes=notes))
        total_vote += vote

    # Conflicts (pairwise).
    for a, b in itertools.combinations(runs, 2):
        da = a.signal.get("direction")
        db = b.signal.get("direction")
        if da in ("bullish", "bearish") and db in ("bullish", "bearish") and da != db:
            conflicts.append(
                {
                    "models": [a.name, b.name],
                    "directions": [da, db],
                    "notes": "方向冲突：一个看多一个看空",
                }
            )

    # Decide fused direction.
    if force_neutral:
        fused_direction = "neutral"
    else:
        fused_direction = "bullish" if total_vote >= threshold else "bearish" if total_vote <= -threshold else "neutral"

    # Confidence mapping: use magnitude of total_vote and model agreement.
    agreement = _agreement_matrix(runs)
    agreement_score = sum(1 for r in runs if r.signal.get("direction") == fused_direction) / max(1, len(runs))
    fused_conf = clamp(0.35 + min(1.0, abs(total_vote) / max(threshold, 1e-6)) * 0.35 + agreement_score * 0.2, 0.2, 0.92)
    if force_neutral:
        fused_conf = min(fused_conf, 0.45)

    # Risk aggregation: promote risk if any model says high/needs review.
    needs_review_any = any(bool((r.signal.get("meta") or {}).get("needs_human_review", False)) for r in runs if isinstance(r.signal.get("meta"), dict))
    risk_levels = [str((r.signal.get("meta") or {}).get("risk_level", "medium")) for r in runs if isinstance(r.signal.get("meta"), dict)]
    fused_risk = "high" if "high" in risk_levels else ("medium" if needs_review_any or "medium" in risk_levels else "low")

    # 聚合子模型证据、风险、发现
    aggregated_evidence = []
    aggregated_risk_notes = []
    aggregated_uncertainties = []
    for r in runs:
        meta = r.signal.get("meta") if isinstance(r.signal.get("meta"), dict) else {}
        for ev in meta.get("evidence") or []:
            if isinstance(ev, dict):
                ev_copy = dict(ev)
                ev_copy["_model"] = r.name
                aggregated_evidence.append(ev_copy)
        for rn in meta.get("risk_notes") or []:
            if rn:
                aggregated_risk_notes.append(f"[{r.name}] {rn}")
        for u in meta.get("uncertainties") or []:
            if u:
                aggregated_uncertainties.append(f"[{r.name}] {u}")

    # 模型名 → 中文简称
    _cn = {
        "volume_price_momentum_analysis": "量价模型",
        "advanced_trend_tracking_system": "趋势模型",
        "oscillator_check": "震荡指标模型",
        "trend_application_dulling_divergence": "钝化背离模型",
    }

    # 生成实质性 key_findings（自然语言）
    gen_key_findings = []
    if fused_direction != "neutral":
        _dir_cn_f = "看多" if fused_direction == "bullish" else "看空"
        gen_key_findings.append(f"融合方向为{_dir_cn_f}，加权投票分{total_vote:+.2f}已跨过±{threshold:.2f}阈值，四模型综合信号明确")
    else:
        if abs(total_vote) < threshold * 0.3:
            gen_key_findings.append(f"融合方向为中性——加权投票分仅{total_vote:+.3f}，远低于±{threshold}阈值，各模型方向分歧显著，尚不足以形成一致的多空判断")
        else:
            gen_key_findings.append(f"融合方向为中性——加权投票分{total_vote:+.3f}接近但未达到±{threshold}阈值，信号强度不足以触发明确的多空方向")
    # 模型方向分布
    bull_names = [r.name for r in runs if r.signal.get("direction") == "bullish"]
    bear_names = [r.name for r in runs if r.signal.get("direction") == "bearish"]
    neutral_names = [r.name for r in runs if r.signal.get("direction") == "neutral"]
    if bull_names:
        _total_bw = sum(r.effective_weight for r in runs if r.name in bull_names)
        gen_key_findings.append(f"看多方：{'、'.join(_cn.get(n,n) for n in bull_names)}（合计有效权重{_total_bw:.0%}），提供了{sum(r.vote for r in runs if r.name in bull_names):+.3f}的正向投票")
    if bear_names:
        _total_bw = sum(r.effective_weight for r in runs if r.name in bear_names)
        gen_key_findings.append(f"看空方：{'、'.join(_cn.get(n,n) for n in bear_names)}（合计有效权重{_total_bw:.0%}），提供了{sum(r.vote for r in runs if r.name in bear_names):+.3f}的负向投票")
    if neutral_names:
        gen_key_findings.append(f"中性方：{'、'.join(_cn.get(n,n) for n in neutral_names)}，未提供方向性投票")
    if conflicts:
        gen_key_findings.append(f"存在{len(conflicts)}处方向冲突，一致性得分仅{agreement_score:.0%}，模型间意见分歧需要关注")
    else:
        gen_key_findings.append(f"本轮未出现方向性冲突，一致性得分{agreement_score:.0%}")
    if fused_risk == "high":
        gen_key_findings.append(f'融合风险评级为"高"——至少一个子模型发出高危信号，建议进行人工复核')
    if gates_triggered:
        gen_key_findings.append(f"本轮触发{len(gates_triggered)}项门控规则，部分子模型的权重或方向受到了动态限制")
    # 聚合子模型发现
    for r in runs:
        meta = r.signal.get("meta") if isinstance(r.signal.get("meta"), dict) else {}
        for kf in meta.get("key_findings") or []:
            if kf and kf not in ("数据不足", "融合输出包含总信号 + 子信号 + 交叉验证报告。", "采用门控（ADX/冲突）+ 加权投票。"):
                gen_key_findings.append(f" {_cn.get(r.name, r.name)}发现：{kf}")

    # =================================================================
    # 融合 reasoning：分析结论式叙述
    # =================================================================
    _target = str((next(iter(model_signals.values()), {}) or {}).get("meta", {}).get("target", "")) if model_signals else ""

    # 1. 收集各方向模型的结论与支撑指标
    _bullish_points = []
    _bearish_points = []
    _neutral_points = []
    _concerns = []  # 风险关注点

    for r in runs:
        sig = r.signal
        meta = sig.get("meta") if isinstance(sig.get("meta"), dict) else {}
        _model_cn = _cn.get(r.name, r.name)
        _dir = str(sig.get("direction", "neutral"))

        # 从 sub_signals 提取具体指标
        subs = meta.get("sub_signals") or {}

        if _dir == "bullish":
            _details = ""
            if r.name == "volume_price_momentum_analysis":
                _obv = subs.get("obv", {})
                _adl = subs.get("ad_line", {})
                _cmf = subs.get("cmf", {})
                _vwap = subs.get("vwap", {})
                _detail_parts = []
                if _obv.get("direction") == "bullish":
                    _detail_parts.append(f"OBV能量潮上升，资金持续流入")
                if _adl.get("direction") == "bullish":
                    _detail_parts.append(f"A/D腾落线同步攀升，买盘占优")
                if _vwap.get("direction") == "bullish":
                    _detail_parts.append(f"价格站稳VWAP均价（偏离{_vwap.get('deviation_pct',0):.0f}%）")
                if _cmf.get("zone") in ("mild_inflow", "strong_inflow"):
                    _detail_parts.append(f"CMF资金流指标偏多")
                _details = "：其" + "，".join(_detail_parts) if _detail_parts else ""
                _concern = ""
                if _vwap.get("deviation_pct", 0) > 30:
                    _concern = "，但VWAP偏离较大需关注高位回落风险"
                _bullish_points.append(f"量价模型看多（置信度{sig.get('confidence',0):.0%}）{_details}{_concern}")
            elif r.name == "advanced_trend_tracking_system":
                _adx_v = subs.get("adx14", {}).get("latest_value", 0)
                _ma60_v = subs.get("ma60", {}).get("latest_value", 0)
                _macd = subs.get("macd", {})
                _detail_parts = []
                if _adx_v and float(_adx_v) >= 20:
                    _detail_parts.append(f"ADX={_adx_v}趋势环境明确")
                if subs.get("ma60", {}).get("above"):
                    _detail_parts.append(f"价格站上MA60均线({_ma60_v})")
                if float(_macd.get("dif", 0)) > float(_macd.get("dea", 0)):
                    _detail_parts.append(f"MACD动能维持多头")
                _details = "：其" + "，".join(_detail_parts) if _detail_parts else ""
                _bullish_points.append(f"趋势模型看多（置信度{sig.get('confidence',0):.0%}）{_details}")
            else:
                _bullish_points.append(f"{_model_cn}看多（置信度{sig.get('confidence',0):.0%}），合计权重{r.effective_weight:.0%}")

        elif _dir == "bearish":
            if r.name == "trend_application_dulling_divergence":
                _div = subs.get("divergence", {})
                _detail_parts = []
                if _div.get("rsi", {}).get("bearish_divergence"):
                    _detail_parts.append(f"RSI顶背离（{_div['rsi'].get('span_days','')}日跨度）")
                if _div.get("macd", {}).get("bearish_divergence"):
                    _detail_parts.append(f"MACD顶背离（{_div['macd'].get('span_days','')}日跨度）")
                if _div.get("rsi", {}).get("bullish_divergence"):
                    _detail_parts.append(f"RSI底背离")
                if _div.get("macd", {}).get("bullish_divergence"):
                    _detail_parts.append(f"MACD底背离")
                _detail_str = "，".join(_detail_parts) if _detail_parts else "无具体指标异常"
                _bearish_points.append(f"钝化背离模型发出风险信号：{_detail_str}")
            else:
                _bearish_points.append(f"{_model_cn}看空（置信度{sig.get('confidence',0):.0%}）")

        else:  # neutral
            if r.name == "oscillator_check":
                _osc_rsi = subs.get("rsi14", {}).get("latest_value", 0)
                _osc_k = subs.get("kdj", {}).get("k", 0)
                _osc_d = subs.get("kdj", {}).get("d", 0)
                _osc_roc = subs.get("roc12", {}).get("latest_value", 0)
                _osc_details = []
                if float(_osc_rsi) > 70:
                    _osc_details.append(f"RSI偏高({_osc_rsi})")
                elif float(_osc_rsi) < 30:
                    _osc_details.append(f"RSI偏低({_osc_rsi})")
                if float(_osc_k) > 80 and float(_osc_d) > 80:
                    _osc_details.append(f"KDJ处于超买区")
                elif float(_osc_k) < 20 and float(_osc_d) < 20:
                    _osc_details.append(f"KDJ处于超卖区")
                if _osc_details:
                    _neutral_points.append(f"震荡指标模型中性（置信度{sig.get('confidence',0):.0%}），部分指标处于极端区域：{'，'.join(_osc_details)}，暗示短期或有转折")
                else:
                    _neutral_points.append(f"震荡指标模型中性（置信度{sig.get('confidence',0):.0%}），指标运行于正常区间，未出现极端信号")
            elif r.name == "trend_application_dulling_divergence":
                _neutral_points.append(f"钝化背离模型中性，未检测到明显钝化或背离，动能与价格方向未出现显著矛盾")
            else:
                _neutral_points.append(f"{_model_cn}中性（置信度{sig.get('confidence',0):.0%}）")

        # 收集各模型风险提示
        for rn in meta.get("risk_notes") or []:
            _clean_rn = rn.rstrip("。；").strip()
            if _clean_rn and _clean_rn not in _concerns:
                _concerns.append(_clean_rn)

    # 2. 组装分析结论
    _lines = []

    # 看多方面
    if _bullish_points:
        _lines.append("看多因素：" + "；".join(_bullish_points))
    if _bearish_points:
        _lines.append("看空/风险因素：" + "；".join(_bearish_points))
    if _neutral_points:
        _lines.append("中性/观望因素：" + "；".join(_neutral_points))

    # 融合结果
    if fused_direction == "bullish":
        _lines.append(f"综合来看，看多力量占据主导，融合方向判定为看多，置信度{fused_conf:.0%}")
    elif fused_direction == "bearish":
        _lines.append(f"综合来看，看空/风险因素更突出，融合方向判定为看空，置信度{fused_conf:.0%}")
    else:
        _total_bull_w = sum(r.effective_weight for r in runs if r.signal.get("direction") == "bullish")
        _total_bear_w = sum(r.effective_weight for r in runs if r.signal.get("direction") == "bearish")
        if force_neutral:
            _lines.append(f"虽然看多模型合计权重{_total_bull_w:.0%}、看空权重{_total_bear_w:.0%}，但因震荡指标内部存在多空冲突触发门控保护，融合层采取保守策略，判定为中性")
        elif _total_bull_w > _total_bear_w:
            _lines.append(f"看多模型权重{_total_bull_w:.0%}高于看空权重{_total_bear_w:.0%}，但综合投票强度未达阈值，当前信号不足以形成明确的交易方向，判定为中性")
        else:
            _lines.append(f"多空力量基本均衡，综合投票强度未达阈值，判定为中性")

    # 风险概览
    if _concerns:
        _unique_concerns = list(dict.fromkeys(_concerns))[:3]
        _lines.append(f"需关注的风险点：{'；'.join(_unique_concerns)}")

    # 后续观察建议
    if fused_direction == "neutral":
        _observe = []
        # 从趋势模型提取建议
        for r in runs:
            subs = (r.signal.get("meta") or {}).get("sub_signals") or {}
            if r.name == "advanced_trend_tracking_system":
                _adx_val = float(subs.get("adx14", {}).get("latest_value", 0))
                if _adx_val >= 25:
                    _observe.append(f"ADX目前{_adx_val:.0f}，若继续维持25以上且MACD柱状图不转负，中期趋势支撑有效")
                elif _adx_val >= 20:
                    _observe.append(f"关注ADX能否站稳25以上以确认趋势延续")
            if r.name == "trend_application_dulling_divergence":
                _div = subs.get("divergence", {})
                if _div.get("rsi", {}).get("bearish_divergence") or _div.get("macd", {}).get("bearish_divergence"):
                    _observe.append("密切跟踪MACD柱状图和RSI走势，若顶背离信号消失且指标重回升势，可重新评估看多信号")
            if r.name == "oscillator_check":
                _rsi = float(subs.get("rsi14", {}).get("latest_value", 0))
                _k = float(subs.get("kdj", {}).get("k", 0))
                if _rsi > 60:
                    _observe.append(f"震荡指标中RSI为{_rsi:.0f}偏强但仍未超买，关注是否会突破70进入超买区")
                if _k > 80:
                    _observe.append(f"KDJ-K值已达{_k:.0f}接近超买，若后续J线拐头向下则短期回调概率增大")
        if not _observe:
            _observe.append("建议等待各子模型方向趋于一致、总投票分接近阈值时再重新评估")
        _lines.append(f"后续观察建议：{'；'.join(_observe)}")

    fused_reasoning = "。".join(_lines).rstrip("。") + "。"

    # Compose fused Signal JSON.
    fused_signal: Signal = {
        "direction": fused_direction,
        "confidence": round(float(fused_conf), 4),
        "reasoning": fused_reasoning,
        "signals": [
            f"total_vote={total_vote:.4f}",
            f"threshold={threshold:.2f}",
            f"gates_triggered={len(gates_triggered)}",
            f"conflicts={len(conflicts)}",
        ],
        "source": "traditional_model_fusion_v0_1",
        "signal_type": "technical",
        "stock_code": str((next(iter(model_signals.values()), {}) or {}).get("stock_code", "")),
        "weight": 1.0,
        "meta": {
            "output_version": "0.1",
            "skill_name": "traditional_model_fusion_v0_1",
            "owner_group": "专家2组（指标）",
            "target": str((next(iter(model_signals.values()), {}) or {}).get("meta", {}).get("target", "")) if model_signals else "",
            "period": str((next(iter(model_signals.values()), {}) or {}).get("meta", {}).get("period", "")) if model_signals else "",
            "time_horizon": "mid",
            "risk_level": fused_risk,
            "key_findings": gen_key_findings,
            "evidence": aggregated_evidence,
            "risk_notes": aggregated_risk_notes,
            "uncertainties": aggregated_uncertainties,
            "needs_human_review": bool(needs_review_any or force_neutral),
            "sub_signals": {
                "total_vote": total_vote,
                "threshold": threshold,
                "agreement_score": agreement_score,
            },
        },
    }

    out_model_signals = [
        {
            "name": r.name,
            "signal": r.signal,
            "base_weight": r.base_weight,
            "effective_weight": r.effective_weight,
            "vote": r.vote,
            "notes": r.notes,
        }
        for r in runs
    ]

    validation_report = {
        "agreement_matrix": agreement,
        "conflicts": conflicts,
        "gates_triggered": gates_triggered,
        "final_thresholds": {
            "threshold": threshold,
            "base_weights": base_weights,
            "effective_weights": effective,
        },
        "total_vote": total_vote,
    }

    return {"fused_signal": fused_signal, "model_signals": out_model_signals, "validation_report": validation_report}
