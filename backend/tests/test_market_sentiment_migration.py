from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text


def test_alembic_head_creates_market_sentiment_tables(monkeypatch, tmp_path):
    db_path = tmp_path / "market_sentiment_upgrade.sqlite3"
    db_url = f"sqlite:///{db_path.as_posix()}"

    import app.config as app_config

    monkeypatch.setattr(app_config, "DATABASE_PATH", db_path)
    monkeypatch.setattr(app_config, "DATABASE_URL", db_url)

    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO alembic_version (version_num) VALUES ('e9f0a1b2c3d4')"
            )
        )

    backend_root = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(backend_root / "alembic.ini"))

    command.upgrade(alembic_cfg, "head")

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    limit_event_indexes = {
        index["name"] for index in inspector.get_indexes("limit_event_daily")
    }
    theme_heat_indexes = {
        index["name"] for index in inspector.get_indexes("theme_heat_daily")
    }
    sentiment_indexes = {
        index["name"] for index in inspector.get_indexes("market_sentiment_daily")
    }
    sentiment_columns = {
        column["name"] for column in inspector.get_columns("market_sentiment_daily")
    }

    assert {"limit_event_daily", "theme_heat_daily", "market_sentiment_daily"}.issubset(tables)
    assert {
        "ix_limit_event_trade_date",
        "ix_limit_event_code_date",
        "ix_limit_event_type_date",
    }.issubset(limit_event_indexes)
    assert {
        "ix_theme_heat_trade_date",
        "ix_theme_heat_code_date",
    }.issubset(theme_heat_indexes)
    assert {
        "ix_market_sentiment_trade_date",
    }.issubset(sentiment_indexes)
    assert {
        "trade_date",
        "max_limit_height",
        "broken_rate",
        "main_theme_name",
        "notes_json",
    }.issubset(sentiment_columns)

    script_dir = ScriptDirectory.from_config(alembic_cfg)
    assert len(script_dir.get_heads()) == 1
