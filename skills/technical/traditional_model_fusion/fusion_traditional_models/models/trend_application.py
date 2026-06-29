from __future__ import annotations

import math
from typing import List

import numpy as np

from ..types import OhlcvRow, Signal
from ..utils import clamp, detect_divergence, kdj, macd, rsi, to_iso_date


SKILL_NAME = "trend_application_dulling_divergence"
OWNER_GROUP = "专家2组（指标）"


def _col(rows: List[OhlcvRow], key: str) -> np.ndarray:
    return np.asarray([float(rows[i].get(key, math.nan)) for i in range(len(rows))], dtype=float)


def analyze(rows: List[OhlcvRow], stock_code: str = "", target: str = "", source_name: str = "uploaded") -> Signal:
    """
    Combine two reusable concepts:
    - KDJ/RSI dulling detection + 대응策略提示
    - RSI/MACD divergence detection (risk warning)

    This module is intentionally "risk/strategy oriented" and should have lower fusion weight.
    """
    if not rows or len(rows) < 30:
        return {
            "direction": "neutral",
            "confidence": 0.25,
            "reasoning": "数据不足（<30 根），无法判断钝化/背离。",
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
    dif, dea, hist = macd(close, 12, 26, 9)

    last_rsi = float(rsi14[-1])
    last_k = float(k[-1])
    last_d = float(d[-1])
    last_hist = float(hist[-1])

    uncertainties: List[str] = []
    risk_notes: List[str] = []
    signals: List[str] = []
    key_findings: List[str] = []
    needs_review = False

    # Dulling detection: extreme zone for >=3 bars
    dull_kdj_high = bool(np.all(k[-3:] > 80) and np.all(d[-3:] > 80))
    dull_kdj_low = bool(np.all(k[-3:] < 20) and np.all(d[-3:] < 20))
    dull_rsi_high = bool(np.all(rsi14[-3:] > 70))
    dull_rsi_low = bool(np.all(rsi14[-3:] < 30))

    dulling = False
    if dull_kdj_high or dull_rsi_high:
        dulling = True
        signals.append("高位钝化迹象（KDJ/RSI）")
        risk_notes.append("高位钝化可能意味着趋势很强，但回撤风险上升；建议用趋势指标二次验证。")
        key_findings.append("高位钝化：建议关注 MACD/均线/量价配合。")
    if dull_kdj_low or dull_rsi_low:
        dulling = True
        signals.append("低位钝化迹象（KDJ/RSI）")
        risk_notes.append("低位钝化可能意味着弱势延续；等待二次确认或更大周期验证。")
        key_findings.append("低位钝化：建议切换更大周期验证。")

    # Divergence detection using RSI and MACD hist
    div_rsi = detect_divergence(close, rsi14, lookback=5)
    div_macd = detect_divergence(close, hist, lookback=5)

    if div_rsi["bearish_divergence"] or div_macd["bearish_divergence"]:
        signals.append("顶背离风险（RSI/MACD）")
        risk_notes.append("检测到顶背离：动能衰竭风险上升，注意减仓/止损。")
        needs_review = True
    if div_rsi["bullish_divergence"] or div_macd["bullish_divergence"]:
        signals.append("底背离机会（RSI/MACD）")
        risk_notes.append("检测到底背离：动能衰竭后可能反弹，但需右侧确认。")
        needs_review = True

    # Direction: this module should be conservative; default neutral unless clear risk/opportunity
    direction = "neutral"
    if any("顶背离" in s for s in signals):
        direction = "bearish"
    elif any("底背离" in s for s in signals):
        direction = "bullish"
    else:
        direction = "neutral"

    confidence = 0.55 if direction != "neutral" else 0.4
    if dulling:
        confidence -= 0.05
        uncertainties.append("钝化信号解释依赖市场环境与周期切换，建议人工复核。")
        needs_review = True
    if needs_review:
        confidence -= 0.1
    confidence = clamp(confidence, 0.25, 0.85)

    risk_level = "high" if needs_review and risk_notes else ("medium" if risk_notes else "low")

    evidence = [
        {"source_type": "market_data", "source_name": source_name, "date": evidence_date, "metric": "RSI(14)", "value": f"{last_rsi:.2f}", "comparison": "dulling>70/<30", "note": "钝化辅助"},
        {"source_type": "market_data", "source_name": source_name, "date": evidence_date, "metric": "KDJ(K,D)", "value": f"{last_k:.2f},{last_d:.2f}", "comparison": "dulling>80/<20", "note": "钝化辅助"},
        {"source_type": "market_data", "source_name": source_name, "date": evidence_date, "metric": "MACD(HIST)", "value": f"{last_hist:.4f}", "comparison": "divergence check", "note": "背离辅助"},
    ]

    period = f"{dates[0]} 至 {dates[-1]}" if dates else ""
    # 自然语言推理：钝化与背离检测结果
    _parts = []
    if dull_kdj_high or dull_rsi_high:
        _d = []
        if dull_kdj_high:
            _d.append("KDJ(K值{:.0f},D值{:.0f})均已连续3日站上80高位".format(last_k, last_d))
        if dull_rsi_high:
            _d.append("RSI已连续3日高于70")
        _parts.append("检测到高位钝化信号：" + "、".join(_d) + "，说明当前趋势虽强但超买风险在积累，需用趋势指标二次确认")
    elif dull_kdj_low or dull_rsi_low:
        _d = []
        if dull_kdj_low:
            _d.append("KDJ(K值{:.0f},D值{:.0f})均已连续3日低于20低位".format(last_k, last_d))
        if dull_rsi_low:
            _d.append("RSI已连续3日低于30")
        _parts.append("检测到低位钝化信号：" + "、".join(_d) + "，弱势可能延续，建议等待右侧确认信号")
    else:
        _parts.append("未检测到KDJ或RSI钝化信号，当前指标未在极端区域持续运行")
    if div_rsi.get("bearish_divergence") or div_macd.get("bearish_divergence"):
        _d = []
        if div_rsi.get("bearish_divergence"):
            _d.append(f"RSI顶背离(价格创新高但RSI走弱，{div_rsi.get('span_days','?')}日跨度)")
        if div_macd.get("bearish_divergence"):
            _d.append(f"MACD顶背离(价格新高、柱状图衰减，{div_macd.get('span_days','?')}日跨度)")
        _parts.append("检测到顶背离：" + "；".join(_d) + "，动能正在衰竭，注意减仓或设置止损")
    elif div_rsi.get("bullish_divergence") or div_macd.get("bullish_divergence"):
        _d = []
        if div_rsi.get("bullish_divergence"):
            _d.append(f"RSI底背离(价格新低但RSI企稳，{div_rsi.get('span_days','?')}日跨度)")
        if div_macd.get("bullish_divergence"):
            _d.append(f"MACD底背离(价格新低、柱状图收窄，{div_macd.get('span_days','?')}日跨度)")
        _parts.append("检测到底背离：" + "；".join(_d) + "，下跌动能衰退，可能酝酿反弹，但需等待右侧确认")
    else:
        _parts.append("未检测到RSI或MACD背离信号，动能方向与价格方向未出现明显背离")
    _dir_cn = "看空（顶背离风险）" if direction == "bearish" else "看多（底背离机会）" if direction == "bullish" else "中性（无明显背离方向）"
    reasoning = f"{'。'.join(_parts)}。综合判断方向为{_dir_cn}，置信度{confidence:.2f}。"

    return {
        "direction": direction,
        "confidence": round(float(confidence), 4),
        "reasoning": reasoning,
        "signals": signals[:10] if signals else ["无明显钝化/背离信号"],
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
            "sub_signals": {
                "dulling": {"kdj_high": dull_kdj_high, "kdj_low": dull_kdj_low, "rsi_high": dull_rsi_high, "rsi_low": dull_rsi_low},
                "divergence": {
                    "rsi": div_rsi,
                    "macd": div_macd,
                },
            },
        },
    }

