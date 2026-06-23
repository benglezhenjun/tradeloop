from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_alembic_head_creates_v8_tables_and_rebuilds_financial(monkeypatch, tmp_path):
    db_path = tmp_path / "v7_upgrade.sqlite3"
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
                "INSERT INTO alembic_version (version_num) VALUES ('d8e9f0a1b2c3')"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE stock_financial ("
                "ts_code VARCHAR(20) NOT NULL,"
                "ann_date VARCHAR(8) NOT NULL,"
                "end_date VARCHAR(8) NOT NULL,"
                "profit_dedt FLOAT,"
                "revenue FLOAT,"
                "updated_at DATETIME,"
                "PRIMARY KEY (ts_code, ann_date, end_date)"
                ")"
            )
        )
        conn.execute(text("CREATE INDEX ix_financial_code ON stock_financial (ts_code)"))
        conn.execute(text("CREATE INDEX ix_financial_end_date ON stock_financial (end_date)"))

    backend_root = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(backend_root / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    financial_columns = {column["name"] for column in inspector.get_columns("stock_financial")}
    top_list_unique_constraints = inspector.get_unique_constraints("top_list")

    assert {"daily_indicator", "daily_moneyflow", "top_list", "top_list_detail"}.issubset(tables)
    assert {"eps", "gross_margin", "current_ratio", "netdebt", "update_flag"}.issubset(
        financial_columns
    )
    assert len(financial_columns) >= 50
    assert any(
        constraint["name"] == "uq_toplist_ts_date_reason"
        and constraint["column_names"] == ["ts_code", "trade_date", "reason"]
        for constraint in top_list_unique_constraints
    )
