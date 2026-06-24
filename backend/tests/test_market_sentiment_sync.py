from unittest.mock import patch

import pandas as pd
import pytest


def insert_quote_dates(db, trade_dates: list[str]):
    from app.models import DailyQuote

    for trade_date in trade_dates:
        db.add(
            DailyQuote(
                ts_code="600000.SH",
                trade_date=trade_date,
                open=10.0,
                high=10.5,
                low=9.8,
                close=10.2,
                vol=1000.0,
                amount=2000.0,
                pct_chg=1.0,
                total_mv=500000.0,
                turnover_rate=1.2,
            )
        )
    db.commit()


class FakeLimitEventEmptyPro:
    def limit_list_d(self, trade_date, fields):
        assert trade_date == "20260407"
        assert "limit" in fields
        assert "open_times" in fields
        return pd.DataFrame()


class FakeLimitEventReplacePro:
    def limit_list_d(self, trade_date, fields):
        assert trade_date == "20260407"
        assert "fd_amount" in fields
        return pd.DataFrame(
            [
                {
                    "ts_code": "600000.SH",
                    "trade_date": trade_date,
                    "name": "PF Bank",
                    "limit": "U",
                    "limit_times": 2,
                    "up_stat": "2/2",
                    "first_time": "093100",
                    "last_time": "145600",
                    "open_times": 0,
                    "fd_amount": 1.5,
                }
            ]
        )


class FakeThemeHeatPro:
    def ths_hot(self, trade_date, market, fields, is_new):
        assert trade_date == "20260407"
        assert market == "概念板块"
        assert is_new == "N"
        assert "ts_name" in fields
        assert "hot" in fields
        return pd.DataFrame(
            [
                {
                    "trade_date": trade_date,
                    "ts_code": "BK001",
                    "ts_name": "机器人",
                    "rank": 1,
                    "hot": 124.0,
                    "concept": '["机器人","AI"]',
                    "rank_reason": "热榜上升",
                }
            ]
        )


class FakeLimitEventBackfillPro:
    def limit_list_d(self, trade_date, fields):
        assert "limit" in fields
        return pd.DataFrame(
            [
                {
                    "ts_code": "600000.SH",
                    "trade_date": trade_date,
                    "name": f"Name-{trade_date}",
                    "limit": "U",
                    "limit_times": 1,
                    "up_stat": "1/1",
                    "first_time": "093000",
                    "last_time": "145700",
                    "open_times": 0,
                    "fd_amount": 2.0,
                }
            ]
        )


class FakeThemeHeatBackfillPro:
    def ths_hot(self, trade_date, market, fields, is_new):
        assert market == "概念板块"
        assert is_new == "N"
        return pd.DataFrame(
            [
                {
                    "trade_date": trade_date,
                    "ts_code": f"BK-{trade_date}",
                    "ts_name": f"Theme-{trade_date}",
                    "rank": 1,
                    "hot": 88.0,
                    "concept": '["示例题材"]',
                    "rank_reason": "盘后热榜",
                }
            ]
        )


class FakeThemeHeatDuplicatePro:
    def ths_hot(self, trade_date, market, fields, is_new):
        assert trade_date == "20260407"
        assert market == "概念板块"
        assert is_new == "N"
        return pd.DataFrame(
            [
                {
                    "trade_date": trade_date,
                    "ts_code": "BK001",
                    "ts_name": "机器人",
                    "rank": 2,
                    "hot": 110.0,
                    "rank_reason": "21:30 快照",
                    "rank_time": "2026-04-07 21:30:00",
                },
                {
                    "trade_date": trade_date,
                    "ts_code": "BK001",
                    "ts_name": "机器人",
                    "rank": 1,
                    "hot": 120.0,
                    "rank_reason": "22:30 快照",
                    "rank_time": "2026-04-07 22:30:00",
                },
                {
                    "trade_date": trade_date,
                    "ts_code": "BK002",
                    "ts_name": "算力",
                    "rank": 3,
                    "hot": 90.0,
                    "rank_reason": "单条快照",
                    "rank_time": "2026-04-07 22:30:00",
                },
            ]
        )


def test_sync_limit_event_daily_handles_empty_result_and_uses_tushare_token(db):
    from app.services.sync_limit_event import sync_limit_event_daily

    with patch("app.services.sync_limit_event.TUSHARE_TOKEN", "demo-token"), patch(
        "app.services.sync_limit_event.ts.pro_api",
        return_value=FakeLimitEventEmptyPro(),
    ) as mock_pro_api, patch("app.services.sync_limit_event.time.sleep", return_value=None):
        result = sync_limit_event_daily(db, ["20260407"])

    mock_pro_api.assert_called_once_with("demo-token")
    assert result == {
        "synced_dates": 1,
        "successful_dates": 1,
        "failed_dates": [],
        "total_rows": 0,
    }


def test_sync_limit_event_daily_replaces_existing_trade_date_rows(db):
    from app.models import LimitEventDaily
    from app.services.sync_limit_event import sync_limit_event_daily

    db.add(
        LimitEventDaily(
            ts_code="600000.SH",
            trade_date="20260407",
            limit_type="U",
            name="Old",
            limit_times=1,
            source="seed",
        )
    )
    db.commit()

    with patch("app.services.sync_limit_event.TUSHARE_TOKEN", "demo-token"), patch(
        "app.services.sync_limit_event.ts.pro_api",
        return_value=FakeLimitEventReplacePro(),
    ), patch("app.services.sync_limit_event.time.sleep", return_value=None):
        result = sync_limit_event_daily(db, ["20260407"])

    rows = db.query(LimitEventDaily).all()
    assert result["synced_dates"] == 1
    assert result["successful_dates"] == 1
    assert result["failed_dates"] == []
    assert result["total_rows"] == 1
    assert len(rows) == 1
    assert rows[0].name == "PF Bank"
    assert rows[0].limit_times == 2


def test_sync_theme_heat_daily_returns_statistics_and_uses_tushare_token(db):
    from app.models import ThemeHeatDaily
    from app.services.sync_theme_heat import sync_theme_heat_daily

    with patch("app.services.sync_theme_heat.TUSHARE_TOKEN", "demo-token"), patch(
        "app.services.sync_theme_heat.ts.pro_api",
        return_value=FakeThemeHeatPro(),
    ) as mock_pro_api, patch("app.services.sync_theme_heat.time.sleep", return_value=None):
        result = sync_theme_heat_daily(db, ["20260407"])

    mock_pro_api.assert_called_once_with("demo-token")
    rows = db.query(ThemeHeatDaily).all()
    assert result == {
        "synced_dates": 1,
        "successful_dates": 1,
        "failed_dates": [],
        "total_rows": 1,
    }
    assert len(rows) == 1
    assert rows[0].theme_code == "BK001"
    assert rows[0].theme_name == "机器人"
    assert rows[0].score == pytest.approx(124.0)


def test_sync_theme_heat_daily_deduplicates_same_theme_by_latest_rank_time(db):
    from app.models import ThemeHeatDaily
    from app.services.sync_theme_heat import sync_theme_heat_daily

    with patch("app.services.sync_theme_heat.TUSHARE_TOKEN", "demo-token"), patch(
        "app.services.sync_theme_heat.ts.pro_api",
        return_value=FakeThemeHeatDuplicatePro(),
    ), patch("app.services.sync_theme_heat.time.sleep", return_value=None):
        result = sync_theme_heat_daily(db, ["20260407"])

    rows = (
        db.query(ThemeHeatDaily)
        .filter(ThemeHeatDaily.trade_date == "20260407")
        .order_by(ThemeHeatDaily.theme_code.asc())
        .all()
    )
    assert result["failed_dates"] == []
    assert result["successful_dates"] == 1
    assert result["total_rows"] == 2
    assert len(rows) == 2
    assert rows[0].theme_code == "BK001"
    assert rows[0].rank == 1
    assert rows[0].score == pytest.approx(120.0)
    assert rows[0].up_stat == "22:30 快照"


def test_backfill_limit_event_reuses_session_without_nested_transaction_conflict(db):
    from app.services.sync_limit_event import backfill_limit_event

    insert_quote_dates(db, ["20260327", "20260330"])

    def fake_sync(db_session, trade_dates):
        assert db_session.in_transaction() is False
        return {
            "synced_dates": len(trade_dates),
            "successful_dates": len(trade_dates),
            "failed_dates": [],
            "total_rows": len(trade_dates),
        }

    with patch("app.services.sync_limit_event.sync_limit_event_daily", side_effect=fake_sync):
        result = backfill_limit_event(db, start_date="20260327")

    assert result["synced_dates"] == 2
    assert result["successful_dates"] == 2
    assert result["failed_dates"] == []
    assert result["total_rows"] == 2


def test_backfill_theme_heat_reuses_session_without_nested_transaction_conflict(db):
    from app.services.sync_theme_heat import backfill_theme_heat

    insert_quote_dates(db, ["20260327", "20260330"])

    def fake_sync(db_session, trade_dates):
        assert db_session.in_transaction() is False
        return {
            "synced_dates": len(trade_dates),
            "successful_dates": len(trade_dates),
            "failed_dates": [],
            "total_rows": len(trade_dates),
        }

    with patch("app.services.sync_theme_heat.sync_theme_heat_daily", side_effect=fake_sync):
        result = backfill_theme_heat(db, start_date="20260327")

    assert result["synced_dates"] == 2
    assert result["successful_dates"] == 2
    assert result["failed_dates"] == []
    assert result["total_rows"] == 2


def test_sync_daily_calls_market_sentiment_raw_steps_in_order():
    from app.services import data_sync

    calls: list[str] = []

    def record(name):
        def _inner(*args, **kwargs):
            calls.append(name)
            return ["20260407"] if name == "daily_quotes" else {"status": "ok"}

        return _inner

    class DummySession:
        def close(self):
            return None

    with patch.object(data_sync, "SessionLocal", return_value=DummySession()), patch.object(
        data_sync, "sync_stock_basic", record("stock_basic")
    ), patch.object(
        data_sync, "sync_daily_quotes", record("daily_quotes")
    ), patch.object(data_sync, "sync_moneyflow_daily", record("moneyflow")), patch.object(
        data_sync, "sync_toplist_daily", record("toplist")
    ), patch.object(data_sync, "sync_limit_event_daily", record("limit_event")), patch.object(
        data_sync, "sync_theme_heat_daily", record("theme_heat")
    ), patch.object(
        data_sync, "sync_market_sentiment_daily", lambda *args, **kwargs: {"status": "ok"}
    ), patch.object(
        data_sync, "sync_financial_data", side_effect=AssertionError("sync_financial_data should not run in sync_daily")
    ), patch.object(
        data_sync, "sync_indicators_daily", record("indicator")
    ):
        data_sync.sync_daily()

    assert calls == [
        "stock_basic",
        "daily_quotes",
        "moneyflow",
        "toplist",
        "limit_event",
        "theme_heat",
        "indicator",
    ]


def test_sync_daily_calls_market_sentiment_snapshot_after_raw_steps():
    from app.services import data_sync

    calls: list[str] = []

    def record(name):
        def _inner(*args, **kwargs):
            calls.append(name)
            return ["20260407"] if name == "daily_quotes" else {"status": "ok"}

        return _inner

    class DummySession:
        def close(self):
            return None

    with patch.object(data_sync, "SessionLocal", return_value=DummySession()), patch.object(
        data_sync, "sync_stock_basic", record("stock_basic")
    ), patch.object(
        data_sync, "sync_daily_quotes", record("daily_quotes")
    ), patch.object(data_sync, "sync_moneyflow_daily", record("moneyflow")), patch.object(
        data_sync, "sync_toplist_daily", record("toplist")
    ), patch.object(data_sync, "sync_limit_event_daily", record("limit_event")), patch.object(
        data_sync, "sync_theme_heat_daily", record("theme_heat")
    ), patch.object(
        data_sync, "sync_market_sentiment_daily", record("market_sentiment")
    ), patch.object(data_sync, "sync_financial_data", side_effect=AssertionError("sync_financial_data should not run in sync_daily")), patch.object(
        data_sync, "sync_indicators_daily", record("indicator")
    ):
        data_sync.sync_daily()

    assert calls == [
        "stock_basic",
        "daily_quotes",
        "moneyflow",
        "toplist",
        "limit_event",
        "theme_heat",
        "market_sentiment",
        "indicator",
    ]


def test_backfill_all_resets_partial_market_sentiment_raw_tables_before_replay(db):
    from app.models import LimitEventDaily, ThemeHeatDaily
    from app.services.backfill import backfill_all

    db.add(
        LimitEventDaily(
            ts_code="600000.SH",
            trade_date="20260403",
            limit_type="U",
            name="old limit",
            source="seed",
        )
    )
    db.add(
        ThemeHeatDaily(
            theme_code="BK001",
            trade_date="20260403",
            theme_name="old theme",
            source="seed",
        )
    )
    db.commit()

    calls: list[tuple[str, int]] = []

    def fake_limit_event(db_session, *args, **kwargs):
        calls.append(("limit_event", db_session.query(LimitEventDaily).count()))
        return {"limit_event": 1}

    def fake_theme_heat(db_session, *args, **kwargs):
        calls.append(("theme_heat", db_session.query(ThemeHeatDaily).count()))
        return {"theme_heat": 1}

    with patch("app.services.backfill.run_full_sync", return_value={"quotes": 1}), patch(
        "app.services.backfill.backfill_moneyflow", return_value={"moneyflow": 1}
    ), patch("app.services.backfill.backfill_toplist", return_value={"toplist": 1}), patch(
        "app.services.backfill.backfill_limit_event", fake_limit_event
    ), patch("app.services.backfill.backfill_theme_heat", fake_theme_heat), patch(
        "app.services.backfill.backfill_financial", return_value={"financial": 1}
    ), patch("app.services.backfill.backfill_indicators", return_value={"indicator": 1}):
        result = backfill_all(db)

    assert ("limit_event", 0) in calls
    assert ("theme_heat", 0) in calls
    assert result["limit_event_daily"] == {"limit_event": 1}
    assert result["theme_heat_daily"] == {"theme_heat": 1}


def test_backfill_all_resets_market_sentiment_snapshot_table_before_rebuild(db):
    from app.models import MarketSentimentDaily
    from app.services.backfill import backfill_all

    db.add(
        MarketSentimentDaily(
            trade_date="20260403",
            max_limit_height=4,
            max_limit_height_count=1,
            max_limit_height_codes_json='["000001.SZ"]',
            notes_json="{}",
        )
    )
    db.commit()

    calls: list[tuple[str, int]] = []

    def fake_market_sentiment(db_session, *args, **kwargs):
        calls.append(("market_sentiment", db_session.query(MarketSentimentDaily).count()))
        return {"market_sentiment": 1}

    with patch("app.services.backfill.run_full_sync", return_value={"quotes": 1}), patch(
        "app.services.backfill.backfill_moneyflow", return_value={"moneyflow": 1}
    ), patch("app.services.backfill.backfill_toplist", return_value={"toplist": 1}), patch(
        "app.services.backfill.backfill_limit_event", return_value={"limit_event": 1}
    ), patch("app.services.backfill.backfill_theme_heat", return_value={"theme_heat": 1}), patch(
        "app.services.backfill.backfill_market_sentiment", fake_market_sentiment
    ), patch("app.services.backfill.backfill_financial", return_value={"financial": 1}), patch(
        "app.services.backfill.backfill_indicators", return_value={"indicator": 1}
    ):
        result = backfill_all(db)

    assert ("market_sentiment", 0) in calls
    assert result["market_sentiment_daily"] == {"market_sentiment": 1}


def test_backfill_all_runs_market_sentiment_raw_steps_in_order(db):
    from app.services.backfill import backfill_all

    calls: list[str] = []

    def record(name, result):
        def _inner(*args, **kwargs):
            calls.append(name)
            return result

        return _inner

    with patch("app.services.backfill.run_full_sync", record("quotes", {"quotes": 1})), patch(
        "app.services.backfill.backfill_moneyflow", record("moneyflow", {"moneyflow": 1})
    ), patch("app.services.backfill.backfill_toplist", record("toplist", {"toplist": 1})), patch(
        "app.services.backfill.backfill_limit_event", record("limit_event", {"limit_event": 1})
    ), patch(
        "app.services.backfill.backfill_theme_heat", record("theme_heat", {"theme_heat": 1})
    ), patch(
        "app.services.backfill.backfill_market_sentiment",
        record("market_sentiment", {"market_sentiment": 1}),
    ), patch("app.services.backfill.backfill_financial", record("financial", {"financial": 1})), patch(
        "app.services.backfill.backfill_indicators", record("indicator", {"indicator": 1})
    ):
        result = backfill_all(db)

    assert calls == [
        "quotes",
        "moneyflow",
        "toplist",
        "limit_event",
        "theme_heat",
        "market_sentiment",
        "financial",
        "indicator",
    ]
    assert result["daily_quote"] == {"quotes": 1}
    assert result["limit_event_daily"] == {"limit_event": 1}
    assert result["theme_heat_daily"] == {"theme_heat": 1}
    assert result["market_sentiment_daily"] == {"market_sentiment": 1}


def test_try_start_backfill_returns_false_when_sync_lock_held():
    from app.services.backfill import try_start_backfill
    from app.services.data_sync import sync_lock

    acquired = sync_lock.acquire(blocking=False)
    assert acquired is True
    try:
        assert try_start_backfill() is False
    finally:
        sync_lock.release()


def test_backfill_limit_event_and_theme_heat_reuse_same_session_without_nested_transaction(db):
    from app.models import DailyQuote, LimitEventDaily, ThemeHeatDaily
    from app.services.sync_limit_event import backfill_limit_event
    from app.services.sync_theme_heat import backfill_theme_heat

    for trade_date in ("20260403", "20260407"):
        db.add(
            DailyQuote(
                ts_code="600000.SH",
                trade_date=trade_date,
                open=10.0,
                high=10.5,
                low=9.8,
                close=10.2,
                vol=1000,
                amount=200000,
                pct_chg=1.0,
                total_mv=500000,
                turnover_rate=2.0,
            )
        )
    db.commit()

    with patch(
        "app.services.sync_limit_event._get_api",
        return_value=FakeLimitEventBackfillPro(),
    ), patch("app.services.sync_limit_event.time.sleep", return_value=None), patch(
        "app.services.sync_theme_heat._get_api",
        return_value=FakeThemeHeatBackfillPro(),
    ), patch("app.services.sync_theme_heat.time.sleep", return_value=None):
        limit_result = backfill_limit_event(db, start_date="20260403")
        theme_result = backfill_theme_heat(db, start_date="20260403")

    assert limit_result["failed_dates"] == []
    assert limit_result["successful_dates"] == 2
    assert limit_result["total_rows"] == 2
    assert db.query(LimitEventDaily).count() == 2

    assert theme_result["failed_dates"] == []
    assert theme_result["successful_dates"] == 2
    assert theme_result["total_rows"] == 2
    assert db.query(ThemeHeatDaily).count() == 2
