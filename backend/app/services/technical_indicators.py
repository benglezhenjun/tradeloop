"""V8 technical indicator calculations."""

from __future__ import annotations

from copy import deepcopy
from statistics import fmean, pstdev
from typing import Any


# 注意：指标均使用 float 计算，长期序列可能有微小精度偏差，这在技术分析场景下可接受。
DEFAULT_MA_PERIODS = [5, 10, 20, 60, 120, 240]
STATE_WINDOW = 240


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _get_value(item: Any, key: str) -> Any:
    if isinstance(item, dict):
        return item.get(key)
    return getattr(item, key, None)


def _trim_window(values: list[float], size: int) -> list[float]:
    if len(values) <= size:
        return values
    return values[-size:]


def calc_ema(values: list[float], period: int, prev_ema: float | None = None) -> float | None:
    if not values:
        return None

    multiplier = 2 / (period + 1)
    if prev_ema is None:
        ema = values[0]
        iterable = values[1:]
    else:
        ema = prev_ema
        iterable = values

    for value in iterable:
        ema = ema * (1 - multiplier) + value * multiplier
    return ema


def calc_ma_series(closes: list[float], periods: list[int] | None = None) -> dict[int, float | None]:
    if periods is None:
        periods = DEFAULT_MA_PERIODS

    result: dict[int, float | None] = {}
    for period in periods:
        if len(closes) < period:
            result[period] = None
        else:
            result[period] = sum(closes[-period:]) / period
    return result


def calc_macd(
    close: float,
    prev_ema_fast: float | None,
    prev_ema_slow: float | None,
    prev_dea: float | None,
) -> dict[str, float]:
    ema_fast = calc_ema([close], 12, prev_ema_fast)
    ema_slow = calc_ema([close], 26, prev_ema_slow)
    dif = float((ema_fast or 0.0) - (ema_slow or 0.0))
    dea = dif if prev_dea is None else float(prev_dea * 0.8 + dif * 0.2)
    hist = (dif - dea) * 2
    return {
        "ema_fast": float(ema_fast or 0.0),
        "ema_slow": float(ema_slow or 0.0),
        "dif": dif,
        "dea": dea,
        "hist": hist,
    }


def calc_kdj(
    close: float,
    high_9: float,
    low_9: float,
    prev_k: float | None,
    prev_d: float | None,
) -> dict[str, float]:
    if high_9 == low_9:
        rsv = 50.0
    else:
        rsv = (close - low_9) / (high_9 - low_9) * 100

    base_k = 50.0 if prev_k is None else prev_k
    base_d = 50.0 if prev_d is None else prev_d
    k = base_k * (2 / 3) + rsv * (1 / 3)
    d = base_d * (2 / 3) + k * (1 / 3)
    j = 3 * k - 2 * d
    return {"k": k, "d": d, "j": j}


def calc_rsi(
    change: float,
    prev_avg_gain: float | None,
    prev_avg_loss: float | None,
    period: int,
) -> dict[str, float]:
    gain = max(change, 0.0)
    loss = max(-change, 0.0)
    if prev_avg_gain is None:
        avg_gain = gain
    else:
        avg_gain = prev_avg_gain * (period - 1) / period + gain / period
    if prev_avg_loss is None:
        avg_loss = loss
    else:
        avg_loss = prev_avg_loss * (period - 1) / period + loss / period

    if avg_loss == 0:
        rsi = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - 100 / (1 + rs)
    return {"rsi": rsi, "avg_gain": avg_gain, "avg_loss": avg_loss}


def calc_boll(closes_20: list[float]) -> dict[str, float | None]:
    if len(closes_20) < 20:
        return {"upper": None, "mid": None, "lower": None}
    mid = fmean(closes_20)
    std = pstdev(closes_20)
    return {"upper": mid + 2 * std, "mid": mid, "lower": mid - 2 * std}


def calc_atr(
    high: float,
    low: float,
    prev_close: float | None,
    prev_atr: float | None,
) -> dict[str, float | None]:
    if prev_close is None:
        return {"tr": None, "atr": None}
    tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
    atr = tr if prev_atr is None else prev_atr * 13 / 14 + tr / 14
    return {"tr": tr, "atr": atr}


def calc_obv(close: float, prev_close: float | None, vol: float, prev_obv: float | None) -> float | None:
    if prev_close is None:
        return None
    base = 0.0 if prev_obv is None else prev_obv
    if close > prev_close:
        return base + vol
    if close < prev_close:
        return base - vol
    return base


def calc_volume_ratio(today_vol: float, recent_vols: list[float]) -> float | None:
    if not recent_vols:
        return None
    avg_vol = fmean(recent_vols)
    if avg_vol == 0:
        return None
    return today_vol / avg_vol


def calc_turnover_change(today_rate: float, recent_rates: list[float]) -> float | None:
    if not recent_rates:
        return None
    avg_rate = fmean(recent_rates)
    if avg_rate == 0:
        return None
    return today_rate / avg_rate


def calculate_stock_indicators(
    quotes: list[dict],
    prev_state: dict | None = None,
) -> tuple[list[dict[str, float | None]], dict[str, Any]]:
    state = deepcopy(prev_state) if prev_state else {}
    closes = list(state.get("closes", []))
    highs = list(state.get("highs", []))
    lows = list(state.get("lows", []))
    vols = list(state.get("vols", []))
    turnover_rates = list(state.get("turnover_rates", []))

    ema_fast = state.get("ema_fast")
    ema_slow = state.get("ema_slow")
    dea = state.get("dea")
    k_value = state.get("k")
    d_value = state.get("d")
    atr_value = state.get("atr")
    obv_value = state.get("obv")
    prev_close = state.get("prev_close")

    rsi_state = {
        6: {
            "avg_gain": state.get("rsi_6_avg_gain"),
            "avg_loss": state.get("rsi_6_avg_loss"),
        },
        12: {
            "avg_gain": state.get("rsi_12_avg_gain"),
            "avg_loss": state.get("rsi_12_avg_loss"),
        },
        24: {
            "avg_gain": state.get("rsi_24_avg_gain"),
            "avg_loss": state.get("rsi_24_avg_loss"),
        },
    }

    rows: list[dict[str, float | None]] = []
    for quote in quotes:
        close = float(_get_value(quote, "close") or 0.0)
        high = float(_get_value(quote, "high") or close)
        low = float(_get_value(quote, "low") or close)
        vol = float(_get_value(quote, "vol") or 0.0)
        turnover_rate = float(_get_value(quote, "turnover_rate") or 0.0)

        closes.append(close)
        highs.append(high)
        lows.append(low)
        vols.append(vol)
        turnover_rates.append(turnover_rate)

        recent_vols = vols[-5:]
        recent_rates = turnover_rates[-5:]

        closes = _trim_window(closes, STATE_WINDOW)
        highs = _trim_window(highs, STATE_WINDOW)
        lows = _trim_window(lows, STATE_WINDOW)
        vols = _trim_window(vols, STATE_WINDOW)
        turnover_rates = _trim_window(turnover_rates, STATE_WINDOW)

        ma_values = calc_ma_series(closes)
        macd = calc_macd(close, ema_fast, ema_slow, dea)
        ema_fast = macd["ema_fast"]
        ema_slow = macd["ema_slow"]
        dea = macd["dea"]

        kdj = calc_kdj(close, max(highs[-9:]), min(lows[-9:]), k_value, d_value)
        k_value = kdj["k"]
        d_value = kdj["d"]

        change = 0.0 if prev_close is None else close - prev_close
        rsi_results: dict[int, dict[str, float]] = {}
        for period in (6, 12, 24):
            result = calc_rsi(
                change,
                rsi_state[period]["avg_gain"],
                rsi_state[period]["avg_loss"],
                period,
            )
            rsi_state[period]["avg_gain"] = result["avg_gain"]
            rsi_state[period]["avg_loss"] = result["avg_loss"]
            rsi_results[period] = result

        boll = calc_boll(closes[-20:])
        atr = calc_atr(high, low, prev_close, atr_value)
        atr_value = atr["atr"]
        obv_value = calc_obv(close, prev_close, vol, obv_value)

        row: dict[str, float | None] = {
            "ma5": ma_values[5],
            "ma10": ma_values[10],
            "ma20": ma_values[20],
            "ma60": ma_values[60],
            "ma120": ma_values[120],
            "ma240": ma_values[240],
            "macd_dif": macd["dif"],
            "macd_dea": macd["dea"],
            "macd_hist": macd["hist"],
            "kdj_k": kdj["k"],
            "kdj_d": kdj["d"],
            "kdj_j": kdj["j"],
            "rsi_6": rsi_results[6]["rsi"],
            "rsi_12": rsi_results[12]["rsi"],
            "rsi_24": rsi_results[24]["rsi"],
            "boll_upper": boll["upper"],
            "boll_mid": boll["mid"],
            "boll_lower": boll["lower"],
            "atr_14": atr["atr"],
            "obv": obv_value,
            "volume_ratio": calc_volume_ratio(vol, recent_vols),
            "turnover_change": calc_turnover_change(turnover_rate, recent_rates),
        }

        ts_code = _get_value(quote, "ts_code")
        trade_date = _get_value(quote, "trade_date")
        if ts_code is not None:
            row["ts_code"] = ts_code
        if trade_date is not None:
            row["trade_date"] = trade_date
        rows.append(row)
        prev_close = close

    next_state = {
        "closes": closes,
        "highs": highs,
        "lows": lows,
        "vols": vols,
        "turnover_rates": turnover_rates,
        "ema_fast": ema_fast,
        "ema_slow": ema_slow,
        "dea": dea,
        "k": k_value,
        "d": d_value,
        "atr": atr_value,
        "obv": obv_value,
        "prev_close": prev_close,
        "rsi_6_avg_gain": rsi_state[6]["avg_gain"],
        "rsi_6_avg_loss": rsi_state[6]["avg_loss"],
        "rsi_12_avg_gain": rsi_state[12]["avg_gain"],
        "rsi_12_avg_loss": rsi_state[12]["avg_loss"],
        "rsi_24_avg_gain": rsi_state[24]["avg_gain"],
        "rsi_24_avg_loss": rsi_state[24]["avg_loss"],
    }
    return rows, next_state
