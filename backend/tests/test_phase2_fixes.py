"""Phase 2 金融 bug 修复的红绿测试（2.1/2.2/2.3/2.4a）。"""

from datetime import datetime, timedelta

import json
import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text


@pytest.fixture
def client(db):
    from app.api import position, trade, user_config
    from app.database import get_db

    app = FastAPI()
    app.include_router(trade.router, prefix="/api")
    app.include_router(position.router, prefix="/api")
    app.include_router(user_config.router, prefix="/api")

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def insert_stock(db, ts_code="600000.SH", name="浦发银行"):
    db.execute(
        text(
            "INSERT OR IGNORE INTO stock_basic "
            "(ts_code, name, industry, market, list_date, list_status) "
            "VALUES (:ts_code, :name, '银行', '主板', '20200101', 'L')"
        ),
        {"ts_code": ts_code, "name": name},
    )
    db.commit()


def insert_quote(db, ts_code, trade_date, close):
    db.execute(
        text(
            "INSERT OR IGNORE INTO daily_quote "
            "(ts_code, trade_date, open, high, low, close, vol, amount, pct_chg, total_mv, turnover_rate) "
            "VALUES (:c, :d, :p, :p, :p, :p, 1000, 200000, 0.5, 500000, 1.0)"
        ),
        {"c": ts_code, "d": trade_date, "p": close},
    )
    db.commit()


def insert_consecutive(db, ts_code, end_date, closes):
    """closes 自旧到新，分配到以 end_date 结尾的连续【日历日】。"""
    d0 = datetime.strptime(end_date, "%Y%m%d")
    n = len(closes)
    for i, close in enumerate(closes):
        day = (d0 - timedelta(days=(n - 1 - i))).strftime("%Y%m%d")
        insert_quote(db, ts_code, day, close)


def make_df(ts_code, trade_date, close):
    return pd.DataFrame([{"ts_code": ts_code, "trade_date": trade_date, "close": close}])


def trade_payload(**overrides):
    payload = {
        "ts_code": "600000.SH",
        "stock_name": "浦发银行",
        "direction": "buy",
        "price": 10.0,
        "quantity": 100,
        "trade_date": "2026-01-01",
        "fee": 0.0,
        "note": "测试",
    }
    payload.update(overrides)
    return payload


# ---------- 2.1 multi_ma_alignment 宽松模式 ----------


def test_multi_ma_loose_accepts_short_history_strict_rejects(db):
    from app.services.conditions.multi_ma_alignment import MultiMaAlignment

    cond = MultiMaAlignment()
    closes = [10.0 + i * 0.1 for i in range(80)]  # 升序：近端更高 → 短均在 MA60 之上
    insert_consecutive(db, "600000.SH", "20260401", closes)
    df = make_df("600000.SH", "20260401", closes[-1])

    loose = cond.evaluate(df, db, {"mode": "loose"})
    strict = cond.evaluate(df, db, {"mode": "strict"})

    assert bool(loose.iloc[0]) is True     # 80 个交易日足够判定宽松多头
    assert bool(strict.iloc[0]) is False   # 不足 240 个交易日，严格模式应排除


def test_multi_ma_loose_rejects_insufficient_history(db):
    from app.services.conditions.multi_ma_alignment import MultiMaAlignment

    cond = MultiMaAlignment()
    closes = [10.0 + i * 0.1 for i in range(59)]  # 不足 60 个交易日
    insert_consecutive(db, "600000.SH", "20260401", closes)
    df = make_df("600000.SH", "20260401", closes[-1])

    loose = cond.evaluate(df, db, {"mode": "loose"})
    assert bool(loose.iloc[0]) is False


# ---------- 2.2 交易日窗口（停牌/长假缺口） ----------


def test_ma_proximity_not_dropped_by_calendar_gap(db):
    from app.services.conditions.ma_proximity import MaProximity

    cond = MaProximity()
    # 20 个交易日但跨度 > 40 日历日：5 天在 3 月初，15 天在 1 月（模拟停牌）
    for i in range(5):
        insert_quote(db, "600000.SH", (datetime.strptime("20260305", "%Y%m%d") - timedelta(days=i)).strftime("%Y%m%d"), 10.0)
    for i in range(15):
        insert_quote(db, "600000.SH", (datetime.strptime("20260115", "%Y%m%d") - timedelta(days=i)).strftime("%Y%m%d"), 10.0)

    df = make_df("600000.SH", "20260401", 10.3)  # 现价 10.3 > MA20(10.0)，偏离 3% < 6%
    result = cond.evaluate(df, db, {"ma_period": 20, "deviation_max": 0.06})
    assert bool(result.iloc[0]) is True


def test_ma_slope_gentle_uptrend_with_gap(db):
    from app.services.conditions.ma_slope import MaSlope

    cond = MaSlope()
    # ma_period=5, slope_window=2 → 需 7 个交易日；跨度 > (5+2)*2=14 日历日
    dates = ["20260401", "20260331", "20260330", "20260310", "20260309", "20260308", "20260307"]
    closes = [10.6, 10.5, 10.4, 10.3, 10.2, 10.1, 10.0]  # 与 dates 一一对应（新→旧递减）
    for d, c in zip(dates, closes):
        insert_quote(db, "600000.SH", d, c)

    df = make_df("600000.SH", "20260401", 10.6)
    result = cond.evaluate(df, db, {"ma_period": 5, "slope_window": 2, "slope_max": 0.05})
    assert bool(result.iloc[0]) is True


# ---------- 2.3 JSON 截断提取 ----------


def test_extract_complete_array():
    from app.services.agents.base import _extract_first_json_payload

    out = _extract_first_json_payload('前缀 [{"a": 1}, {"a": 2}] 后缀')
    assert json.loads(out) == [{"a": 1}, {"a": 2}]


def test_extract_markdown_wrapped_array():
    from app.services.agents.base import _extract_first_json_payload

    out = _extract_first_json_payload('```json\n[{"x": 1}]\n```')
    assert json.loads(out) == [{"x": 1}]


def test_extract_single_object():
    from app.services.agents.base import _extract_first_json_payload

    out = _extract_first_json_payload('噪声 {"k": 5} 结束')
    assert json.loads(out) == {"k": 5}


def test_extract_truncated_array_not_returns_first_object():
    from app.services.agents.base import _extract_first_json_payload

    out = _extract_first_json_payload('[{"a": 1}, {"a": 2')  # 截断数组
    assert out != '{"a": 1}'                                 # 不能静默返回首个对象
    with pytest.raises(json.JSONDecodeError):                # 交给上层走降级
        json.loads(out)


# ---------- 2.4a 持仓部分卖出精确摊销 ----------


def test_partial_sell_uses_precise_cost_basis(client, db):
    insert_stock(db, "600000.SH", "浦发银行")
    # 三笔买入造成非整除均价：(1000+1000+1100)/300 = 10.3333...
    client.post("/api/trade", json=trade_payload(price=10.0, quantity=100, fee=0.0, trade_date="2026-01-01"))
    client.post("/api/trade", json=trade_payload(price=10.0, quantity=100, fee=0.0, trade_date="2026-01-02"))
    client.post("/api/trade", json=trade_payload(price=11.0, quantity=100, fee=0.0, trade_date="2026-01-03"))
    # 卖出 100：精确摊销 cost_removed = 3100*100/300 = 1033.33333...
    client.post("/api/trade", json=trade_payload(direction="sell", price=12.0, quantity=100, fee=0.0, trade_date="2026-01-04"))

    pos = client.get("/api/position/600000.SH").json()["position"]
    assert pos["total_quantity"] == 200
    # 精确剩余成本 2066.666667；旧实现用已舍入均价回减会得到 2066.6667（差 ~3.3e-5）
    assert pos["total_cost"] == pytest.approx(2066.666667, abs=1e-5)
    assert pos["realized_pnl"] == pytest.approx(166.666667, abs=1e-5)
