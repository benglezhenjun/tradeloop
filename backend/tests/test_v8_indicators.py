import pytest

from app.services.indicator_calc import (
    calc_atr,
    calc_boll,
    calc_kdj,
    calc_ma_series,
    calc_macd,
    calc_obv,
    calc_rsi,
    calc_turnover_change,
    calc_volume_ratio,
    calculate_stock_indicators,
)


def test_calc_ma_series_handles_normal_and_insufficient_data():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]

    result = calc_ma_series(values, [3, 5, 10])

    assert result[3] == pytest.approx(4.0)
    assert result[5] == pytest.approx(3.0)
    assert result[10] is None


def test_calc_ma_series_handles_empty_input():
    result = calc_ma_series([], [5, 10])

    assert result == {5: None, 10: None}


def test_calc_macd_supports_multi_day_incremental_calculation():
    day1 = calc_macd(close=10.0, prev_ema_fast=None, prev_ema_slow=None, prev_dea=None)
    day2 = calc_macd(
        close=11.0,
        prev_ema_fast=day1["ema_fast"],
        prev_ema_slow=day1["ema_slow"],
        prev_dea=day1["dea"],
    )

    assert day1["dif"] == pytest.approx(0.0)
    assert day1["dea"] == pytest.approx(0.0)
    assert day2["ema_fast"] == pytest.approx(10.1538461538, rel=1e-6)
    assert day2["ema_slow"] == pytest.approx(10.0740740741, rel=1e-6)
    assert day2["dif"] == pytest.approx(0.0797720798, rel=1e-6)
    assert day2["dea"] == pytest.approx(0.01595441596, rel=1e-6)
    assert day2["hist"] == pytest.approx(0.1276353277, rel=1e-6)


def test_calc_kdj_handles_zero_denominator_boundary():
    result = calc_kdj(close=10.0, high_9=10.0, low_9=10.0, prev_k=None, prev_d=None)

    assert result["k"] == pytest.approx(50.0)
    assert result["d"] == pytest.approx(50.0)
    assert result["j"] == pytest.approx(50.0)


def test_calc_rsi_returns_values_between_zero_and_hundred():
    result = calc_rsi(change=2.0, prev_avg_gain=None, prev_avg_loss=None, period=6)

    assert result["rsi"] == pytest.approx(100.0)
    assert 0.0 <= result["rsi"] <= 100.0
    assert result["avg_gain"] == pytest.approx(2.0)
    assert result["avg_loss"] == pytest.approx(0.0)


def test_calc_boll_handles_enough_and_insufficient_data():
    insufficient = calc_boll(list(range(1, 10)))
    result = calc_boll([float(i) for i in range(1, 21)])

    assert insufficient == {"upper": None, "mid": None, "lower": None}
    assert result["mid"] == pytest.approx(10.5)
    assert result["upper"] == pytest.approx(22.03256259, rel=1e-6)
    assert result["lower"] == pytest.approx(-1.03256259, rel=1e-6)


def test_calc_atr_handles_first_and_following_day():
    first = calc_atr(high=12.0, low=9.0, prev_close=10.0, prev_atr=None)
    second = calc_atr(high=13.0, low=10.0, prev_close=11.0, prev_atr=first["atr"])

    assert first["tr"] == pytest.approx(3.0)
    assert first["atr"] == pytest.approx(3.0)
    assert second["tr"] == pytest.approx(3.0)
    assert second["atr"] == pytest.approx(3.0)


def test_calc_atr_and_obv_return_none_when_prev_close_is_missing():
    atr = calc_atr(high=12.0, low=9.0, prev_close=None, prev_atr=None)
    obv = calc_obv(close=10.0, prev_close=None, vol=100.0, prev_obv=None)

    assert atr == {"tr": None, "atr": None}
    assert obv is None


def test_calc_obv_handles_up_down_flat():
    assert calc_obv(close=11.0, prev_close=10.0, vol=100.0, prev_obv=None) == pytest.approx(100.0)
    assert calc_obv(close=9.0, prev_close=10.0, vol=100.0, prev_obv=50.0) == pytest.approx(-50.0)
    assert calc_obv(close=10.0, prev_close=10.0, vol=100.0, prev_obv=25.0) == pytest.approx(25.0)


def test_volume_ratio_and_turnover_change_handle_zero_average():
    assert calc_volume_ratio(200.0, [100.0] * 5) == pytest.approx(2.0)
    assert calc_volume_ratio(200.0, [0.0] * 5) is None
    assert calc_turnover_change(3.0, [2.0] * 5) == pytest.approx(1.5)
    assert calc_turnover_change(3.0, []) is None


def test_calculate_stock_indicators_returns_complete_output_and_state():
    quotes = []
    for i in range(1, 26):
        quotes.append(
            {
                "close": float(i + 9),
                "high": float(i + 10),
                "low": float(i + 8),
                "vol": float(1000 + i * 10),
                "turnover_rate": float(1 + i * 0.1),
            }
        )

    rows, state = calculate_stock_indicators(quotes)

    assert len(rows) == 25
    assert rows[-1]["ma5"] is not None
    assert rows[-1]["macd_dif"] is not None
    assert rows[-1]["kdj_k"] is not None
    assert rows[-1]["rsi_6"] is not None
    assert rows[-1]["boll_mid"] is not None
    assert rows[-1]["atr_14"] is not None
    assert rows[-1]["obv"] is not None
    assert rows[-1]["volume_ratio"] is not None
    assert rows[-1]["turnover_change"] is not None
    assert state["ema_fast"] is not None
    assert state["ema_slow"] is not None
    assert state["dea"] is not None
    assert state["prev_close"] == pytest.approx(34.0)


def test_calculate_stock_indicators_computes_volume_ratio_on_first_row():
    quotes = [
        {
            "close": 10.0,
            "high": 10.5,
            "low": 9.5,
            "vol": 1000.0,
            "turnover_rate": 1.2,
        }
    ]

    rows, state = calculate_stock_indicators(quotes)

    assert rows[0]["volume_ratio"] == pytest.approx(1.0)
    assert state["vols"] == [1000.0]
