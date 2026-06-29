from __future__ import annotations

import math
from typing import List

import numpy as np

from ..types import OhlcvRow, Signal
from ..utils import bollinger, clamp, detect_divergence, kdj, macd, roc, rsi, to_iso_date


SKILL_NAME = "oscillator_check"
OWNER_GROUP = "专家2组（技术分析）"


def _col(rows: List[OhlcvRow], key: str) -> np.ndarray:
    return np.asarray([float(rows[i].get(key, math.nan)) for i in range(len(rows))], dtype=float)


def analyze(rows: List[OhlcvRow], stock_code: str = "", target: str = "", source_name: str = "uploaded") -> Signal:
    if not rows or len(rows) < 30:
        return {
            "direction": "neutral",
            "confidence": 0.25,
            "reasoning": "行情数据不足（<30 根），无法可靠判读震荡类指标。",
            "signals": ["数据不足"],
            "source": SKILL_NAME,
            "signal_type": "technical",
            "stock_code": stock_code,
            "weight": 1.0,
            "meta": {
                "output_version": "0.1",
                "skill_name": SKILL_NAME,
                "owner_group": OWNER_GROUP,
                "target": target or stock_code,
                "period": "",
                "time_horizon": "short",
                "risk_level": "high",
                "key_findings": ["数据不足"],
                "evidence": [],
                "risk_notes": ["数据不足"],
                "uncertainties": ["rows<30"],
                "needs_human_review": True,
            },
        }

    high = _col(rows, "high")
    low = _col(rows, "low")
    close = _col(rows, "close")
    dates = [to_iso_date(r.get("date")) for r in rows]
    evidence_date = dates[-1] if dates else ""

    rsi14 = rsi(close, 14)
    k, d, j = kdj(high, low, close, 9, 3, 3)
    mid, upper, lower = bollinger(close, 20, 2.0)
    dif, dea, hist = macd(close, 12, 26, 9)
    roc12 = roc(close, 12)

    last_rsi = float(rsi14[-1])
    last_k = float(k[-1])
    last_d = float(d[-1])
    last_j = float(j[-1])
    last_close = float(close[-1])
    last_upper = float(upper[-1]) if len(upper) else math.nan
    last_lower = float(lower[-1]) if len(lower) else math.nan
    last_mid = float(mid[-1]) if len(mid) else math.nan
    last_dif = float(dif[-1])
    last_dea = float(dea[-1])
    last_hist = float(hist[-1])
    last_roc = float(roc12[-1]) if len(roc12) else math.nan

    uncertainties: List[str] = []
    risk_notes: List[str] = []
    needs_review = False

    sub_signals = {}
    signals: List[str] = []
    key_findings: List[str] = []

    # RSI
    rsi_dir = "neutral"
    rsi_conf = 0.5
    if last_rsi > 80:
        rsi_dir = "bearish"
        signals.append("RSI 超买")
        risk_notes.append("RSI>80，警惕回调。")
    elif last_rsi < 20:
        rsi_dir = "bullish"
        signals.append("RSI 超卖")
        risk_notes.append("RSI<20，存在反弹概率。")
    sub_signals["rsi14"] = {"direction": rsi_dir, "latest_value": round(last_rsi, 2), "confidence": rsi_conf}

    # KDJ
    kdj_dir = "neutral"
    kdj_conf = 0.55
    if last_k > 80 and last_d > 80:
        kdj_dir = "bearish"
        signals.append("KDJ 超买")
    elif last_k < 20 and last_d < 20:
        kdj_dir = "bullish"
        signals.append("KDJ 超卖")
    # cross
    if len(k) >= 2:
        if k[-2] <= d[-2] and k[-1] > d[-1]:
            signals.append("KDJ 金叉")
            kdj_dir = "bullish"
            kdj_conf = 0.7 if last_k < 20 and last_d < 20 else 0.6
        if k[-2] >= d[-2] and k[-1] < d[-1]:
            signals.append("KDJ 死叉")
            kdj_dir = "bearish"
            kdj_conf = 0.7 if last_k > 80 and last_d > 80 else 0.6
    sub_signals["kdj"] = {"direction": kdj_dir, "k": round(last_k, 2), "d": round(last_d, 2), "j": round(last_j, 2), "confidence": kdj_conf}

    # BOLL
    boll_dir = "neutral"
    boll_conf = 0.55
    if math.isfinite(last_upper) and last_close >= last_upper:
        boll_dir = "bearish"
        signals.append("价格触及/突破BOLL上轨")
    elif math.isfinite(last_lower) and last_close <= last_lower:
        boll_dir = "bullish"
        signals.append("价格触及/跌破BOLL下轨")
    # mid cross
    if len(close) >= 2 and math.isfinite(last_mid) and math.isfinite(float(mid[-2])):
        if close[-2] <= mid[-2] and close[-1] > mid[-1]:
            boll_dir = "bullish"
            signals.append("价格上穿BOLL中轨")
        if close[-2] >= mid[-2] and close[-1] < mid[-1]:
            boll_dir = "bearish"
            signals.append("价格下破BOLL中轨")
    sub_signals["boll"] = {"direction": boll_dir, "mid": round(last_mid, 4) if math.isfinite(last_mid) else None, "upper": round(last_upper, 4) if math.isfinite(last_upper) else None, "lower": round(last_lower, 4) if math.isfinite(last_lower) else None, "confidence": boll_conf}

    # MACD
    macd_dir = "neutral"
    macd_conf = 0.6
    if len(dif) >= 2:
        if dif[-2] <= dea[-2] and dif[-1] > dea[-1]:
            macd_dir = "bullish"
            signals.append("MACD 金叉")
        if dif[-2] >= dea[-2] and dif[-1] < dea[-1]:
            macd_dir = "bearish"
            signals.append("MACD 死叉")
    sub_signals["macd"] = {"direction": macd_dir, "dif": round(last_dif, 4), "dea": round(last_dea, 4), "hist": round(last_hist, 4), "confidence": macd_conf}

    # ROC
    roc_dir = "neutral"
    roc_conf = 0.55
    if math.isfinite(last_roc):
        if last_roc > 0:
            roc_dir = "bullish"
        elif last_roc < 0:
            roc_dir = "bearish"
    sub_signals["roc12"] = {"direction": roc_dir, "latest_value": round(last_roc, 4) if math.isfinite(last_roc) else None, "confidence": roc_conf}

    # Divergence hints
    div_rsi = detect_divergence(close, rsi14, lookback=5)
    div_macd = detect_divergence(close, hist, lookback=5)
    divergence_notes: List[str] = []
    if div_rsi["bearish_divergence"] or div_macd["bearish_divergence"]:
        divergence_notes.append("出现顶背离迹象（RSI/MACD）。")
    if div_rsi["bullish_divergence"] or div_macd["bullish_divergence"]:
        divergence_notes.append("出现底背离迹象（RSI/MACD）。")
    if divergence_notes:
        signals.extend(divergence_notes)
        risk_notes.extend(divergence_notes)

    dirs = [sub_signals[k]["direction"] for k in ("rsi14", "kdj", "boll", "macd", "roc12")]
    bullish = sum(1 for d0 in dirs if d0 == "bullish")
    bearish = sum(1 for d0 in dirs if d0 == "bearish")

    if bullish >= 3 and bearish == 0:
        direction = "bullish"
        confidence = 0.75
        key_findings.append("震荡类多指标一致偏多。")
    elif bearish >= 3 and bullish == 0:
        direction = "bearish"
        confidence = 0.75
        key_findings.append("震荡类多指标一致偏空。")
    else:
        direction = "neutral"
        confidence = 0.45
        key_findings.append("震荡类指标存在分化或冲突。")
        if bullish and bearish:
            uncertainties.append("多空信号冲突（震荡类指标）。")
            needs_review = True

    risk_level = "high" if needs_review else ("medium" if risk_notes else "low")
    confidence = clamp(confidence - (0.1 if needs_review else 0.0), 0.25, 0.95)

    evidence = [
        {"source_type": "market_data", "source_name": source_name, "date": evidence_date, "metric": "RSI(14)", "value": f"{last_rsi:.2f}", "comparison": "thresholds", "note": "超买>80，超卖<20"},
        {"source_type": "market_data", "source_name": source_name, "date": evidence_date, "metric": "KDJ(K,D,J)", "value": f"{last_k:.2f},{last_d:.2f},{last_j:.2f}", "comparison": "thresholds", "note": "超买>80，超卖<20"},
        {"source_type": "market_data", "source_name": source_name, "date": evidence_date, "metric": "BOLL(mid,upper,lower)", "value": f"{last_mid if math.isfinite(last_mid) else ''},{last_upper if math.isfinite(last_upper) else ''},{last_lower if math.isfinite(last_lower) else ''}", "comparison": "touch/break", "note": "触上轨偏空，触下轨偏多"},
        {"source_type": "market_data", "source_name": source_name, "date": evidence_date, "metric": "MACD(DIF,DEA,HIST)", "value": f"{last_dif:.4f},{last_dea:.4f},{last_hist:.4f}", "comparison": "cross", "note": "DIF 上穿 DEA 金叉；下穿死叉"},
        {"source_type": "market_data", "source_name": source_name, "date": evidence_date, "metric": "ROC(12)", "value": "" if not math.isfinite(last_roc) else f"{last_roc:.4f}", "comparison": "zero", "note": "穿越零轴反映动能方向"},
    ]

    period = f"{dates[0]} 至 {dates[-1]}" if dates else ""
    # 自然语言推理：各振荡指标逐一解读
    _parts = []
    if last_rsi > 80:
        _parts.append(f"RSI(14)为{last_rsi:.1f}，进入超买区域，短期回调风险上升")
    elif last_rsi < 20:
        _parts.append(f"RSI(14)为{last_rsi:.1f}，进入超卖区域，存在反弹修复预期")
    else:
        _parts.append(f"RSI(14)为{last_rsi:.0f}，运行于中性区间，未出现极端超买超卖信号")
    if last_k > 80 and last_d > 80:
        _parts.append(f"KDJ指标K值{last_k:.0f}、D值{last_d:.0f}双双高于80，处于超买区")
    elif last_k < 20 and last_d < 20:
        _parts.append(f"KDJ指标K值{last_k:.0f}、D值{last_d:.0f}双双低于20，处于超卖区")
    else:
        _parts.append(f"KDJ指标K={last_k:.0f}、D={last_d:.0f}、J={last_j:.0f}，处于中性区间")
    if math.isfinite(last_mid):
        if math.isfinite(last_upper) and last_close >= last_upper:
            _parts.append(f"价格触及布林带上轨（上轨{last_upper:.1f}、中轨{last_mid:.1f}），短期或有回调压力")
        elif math.isfinite(last_lower) and last_close <= last_lower:
            _parts.append(f"价格触及布林带下轨（下轨{last_lower:.1f}、中轨{last_mid:.1f}），短期或有支撑反弹")
        else:
            _parts.append(f"价格位于布林带中轨({last_mid:.1f}元)附近运行，波动率正常")
    if macd_dir == "bullish":
        _parts.append(f"MACD指标DIF({last_dif:.2f})上穿DEA({last_dea:.2f})，金叉形态，动能偏多")
    elif macd_dir == "bearish":
        _parts.append(f"MACD指标DIF({last_dif:.2f})下穿DEA({last_dea:.2f})，死叉形态，动能偏空")
    else:
        _parts.append(f"MACD指标DIF({last_dif:.2f})与DEA({last_dea:.2f})未形成交叉，动能方向不明确")
    if math.isfinite(last_roc):
        _parts.append(f"ROC(12)变动率为{last_roc:.1f}%，{'动能向上' if last_roc > 0 else '动能向下'}")
    if divergence_notes:
        _parts.append(f"此外，检测到{'；'.join(divergence_notes)}，需要结合趋势方向谨慎判断")
    _dir_cn = "看多" if direction == "bullish" else "看空" if direction == "bearish" else "中性"
    reasoning = (
        f"{'。'.join(_parts)}。"
        f"综合以上，{bullish}个指标偏多、{bearish}个指标偏空，震荡系统整体判断为{_dir_cn}，置信度{confidence:.2f}。"
    )

    return {
        "direction": direction,
        "confidence": round(float(confidence), 4),
        "reasoning": reasoning,
        "signals": signals[:12] if signals else ["无明显信号"],
        "source": SKILL_NAME,
        "signal_type": "technical",
        "stock_code": stock_code,
        "weight": 1.0,
        "meta": {
            "output_version": "0.1",
            "skill_name": SKILL_NAME,
            "owner_group": OWNER_GROUP,
            "target": target or stock_code,
            "period": period,
            "time_horizon": "short",
            "risk_level": risk_level,
            "key_findings": key_findings,
            "evidence": evidence,
            "risk_notes": risk_notes,
            "uncertainties": uncertainties,
            "needs_human_review": needs_review,
            "sub_signals": sub_signals,
        },
    }

