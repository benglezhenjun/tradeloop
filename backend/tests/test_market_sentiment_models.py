from sqlalchemy import create_engine, event, inspect
from sqlalchemy.pool import StaticPool


def make_engine():
    eng = create_engine(
        "sqlite://",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(eng, "connect")
    def _set_pragma(dbapi_connection, _):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    return eng


def test_market_sentiment_raw_models_create_expected_tables():
    eng = make_engine()
    try:
        import app.models  # noqa: F401
        from app.database import Base

        Base.metadata.create_all(bind=eng)

        inspector = inspect(eng)
        tables = set(inspector.get_table_names())
        assert "limit_event_daily" in tables
        assert "theme_heat_daily" in tables
        assert "market_sentiment_daily" in tables
    finally:
        eng.dispose()


def test_market_sentiment_raw_models_expose_primary_keys_and_indexes():
    eng = make_engine()
    try:
        import app.models  # noqa: F401
        from app.database import Base

        Base.metadata.create_all(bind=eng)

        inspector = inspect(eng)

        limit_event_columns = {
            column["name"] for column in inspector.get_columns("limit_event_daily")
        }
        assert {
            "ts_code",
            "trade_date",
            "name",
            "limit_type",
            "limit_times",
            "up_stat",
            "first_time",
            "last_time",
            "open_num",
            "fd_amount",
            "source",
        }.issubset(limit_event_columns)
        limit_event_pk = inspector.get_pk_constraint("limit_event_daily")
        assert set(limit_event_pk["constrained_columns"]) == {"ts_code", "trade_date", "limit_type"}
        limit_event_indexes = {
            index["name"] for index in inspector.get_indexes("limit_event_daily")
        }
        assert {
            "ix_limit_event_trade_date",
            "ix_limit_event_code_date",
            "ix_limit_event_type_date",
        }.issubset(limit_event_indexes)

        theme_columns = {
            column["name"] for column in inspector.get_columns("theme_heat_daily")
        }
        assert {
            "trade_date",
            "theme_code",
            "theme_name",
            "rank",
            "up_nums",
            "cons_nums",
            "up_stat",
            "score",
            "source",
        }.issubset(theme_columns)
        theme_pk = inspector.get_pk_constraint("theme_heat_daily")
        assert set(theme_pk["constrained_columns"]) == {"theme_code", "trade_date"}
        theme_indexes = {
            index["name"] for index in inspector.get_indexes("theme_heat_daily")
        }
        assert {
            "ix_theme_heat_trade_date",
            "ix_theme_heat_code_date",
        }.issubset(theme_indexes)

        sentiment_columns = {
            column["name"] for column in inspector.get_columns("market_sentiment_daily")
        }
        assert {
            "trade_date",
            "max_limit_height",
            "max_limit_height_count",
            "max_limit_height_codes_json",
            "limit_up_count",
            "limit_broken_count",
            "broken_rate",
            "yday_limit_premium_avg",
            "yday_limit_premium_median",
            "yday_limit_red_rate",
            "yday_limit_sample_count",
            "high_board_threshold",
            "high_board_total",
            "high_board_advanced",
            "high_board_promotion_rate",
            "main_theme_code",
            "main_theme_name",
            "main_theme_score",
            "main_theme_streak_days",
            "notes_json",
        }.issubset(sentiment_columns)
        sentiment_pk = inspector.get_pk_constraint("market_sentiment_daily")
        assert sentiment_pk["constrained_columns"] == ["trade_date"]
    finally:
        eng.dispose()
