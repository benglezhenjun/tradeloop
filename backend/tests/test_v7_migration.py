from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


def test_alembic_head_creates_v7_review_tables(monkeypatch, tmp_path):
    """模拟现有 V6 数据库升级到 head，V7 复盘表必须补齐。"""
    db_path = tmp_path / "v6_upgrade.sqlite3"
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
                "INSERT INTO alembic_version (version_num) VALUES ('c7d8e9f0a1b2')"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE trading_plan (id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT)"
            )
        )

    backend_root = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(backend_root / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")

    with engine.connect() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type = 'table'")
            )
        }

    assert "trade_review" in tables
    assert "behavior_pattern" in tables
