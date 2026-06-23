"""通用技术指标计算工具。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def calc_ma(closes: Sequence[float], period: int) -> float:
    if not closes:
        return 0.0
    window = closes[-min(period, len(closes)) :]
    return sum(window) / len(window)


def calc_price_stats(quotes: Sequence[Any]) -> dict[str, float]:
    if not quotes:
        return {
            "latest_close": 0.0,
            "latest_pct": 0.0,
            "latest_amount": 0.0,
            "latest_total_mv": 0.0,
            "ma5": 0.0,
            "ma20": 0.0,
            "ma60": 0.0,
            "high_60": 0.0,
            "low_60": 0.0,
            "pct_30d": 0.0,
            "avg_amount_5d": 0.0,
            "pct_from_high": 0.0,
            "pct_from_low": 0.0,
        }

    latest = quotes[-1]
    closes = [float(q.close) for q in quotes if getattr(q, "close", None) is not None]
    highs = [float(q.high) for q in quotes if getattr(q, "high", None) is not None]
    lows = [float(q.low) for q in quotes if getattr(q, "low", None) is not None]
    pct_window = quotes[-30:]
    pct_30d = sum(float(q.pct_chg) for q in pct_window if getattr(q, "pct_chg", None) is not None)
    amount_window = quotes[-5:]
    recent_amounts = [float(q.amount) for q in amount_window if getattr(q, "amount", None) is not None]

    high_60 = max(highs) if highs else float(getattr(latest, "close", 0) or 0)
    low_60 = min(lows) if lows else float(getattr(latest, "close", 0) or 0)
    latest_close = float(getattr(latest, "close", 0) or 0)

    return {
        "latest_close": latest_close,
        "latest_pct": float(getattr(latest, "pct_chg", 0) or 0),
        "latest_amount": float(getattr(latest, "amount", 0) or 0),
        "latest_total_mv": float(getattr(latest, "total_mv", 0) or 0),
        "ma5": calc_ma(closes, 5),
        "ma20": calc_ma(closes, 20),
        "ma60": calc_ma(closes, 60),
        "high_60": high_60,
        "low_60": low_60,
        "pct_30d": pct_30d,
        "avg_amount_5d": sum(recent_amounts) / len(recent_amounts) if recent_amounts else 0.0,
        "pct_from_high": ((latest_close - high_60) / high_60 * 100) if high_60 else 0.0,
        "pct_from_low": ((latest_close - low_60) / low_60 * 100) if low_60 else 0.0,
    }
