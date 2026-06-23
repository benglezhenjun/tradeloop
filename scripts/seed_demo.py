"""Seed a local TradeLoop database with real Tushare data.

Requires the user's own Tushare token in config/local.toml and network access.
Fetched data is for personal local use only; see DATA_LICENSE.md.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.resolve().as_posix()}"


def resolve_output_path(raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def run_alembic_upgrade(db_path: Path) -> None:
    import app.config as app_config
    from alembic import command
    from alembic.config import Config

    app_config.DATABASE_PATH = db_path
    app_config.DATABASE_URL = sqlite_url(db_path)

    alembic_cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")


def prepare_legacy_base_tables(db_path: Path) -> None:
    """Create legacy base tables that are absent from the current migration chain."""
    engine = create_engine(sqlite_url(db_path), echo=False)
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS stock_basic (
                        ts_code VARCHAR(20) NOT NULL,
                        name VARCHAR(50) NOT NULL,
                        industry VARCHAR(50),
                        market VARCHAR(20),
                        list_date VARCHAR(8),
                        list_status VARCHAR(1),
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (ts_code)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS daily_quote (
                        ts_code VARCHAR(20) NOT NULL,
                        trade_date VARCHAR(8) NOT NULL,
                        open FLOAT,
                        high FLOAT,
                        low FLOAT,
                        close FLOAT,
                        vol FLOAT,
                        amount FLOAT,
                        pct_chg FLOAT,
                        total_mv FLOAT,
                        turnover_rate FLOAT,
                        PRIMARY KEY (ts_code, trade_date)
                    )
                    """
                )
            )
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_daily_trade_date ON daily_quote (trade_date)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_daily_code_date ON daily_quote (ts_code, trade_date)"))
    finally:
        engine.dispose()


def make_session(db_path: Path) -> sessionmaker[Session]:
    engine = create_engine(sqlite_url(db_path), echo=False)

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection: Any, _connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return sessionmaker(bind=engine)


def clean_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    return value.item() if hasattr(value, "item") else value


def stock_codes(raw: str) -> list[str]:
    codes = [item.strip().upper() for item in raw.split(",") if item.strip()]
    if not codes:
        raise argparse.ArgumentTypeError("--stocks 至少需要一个 ts_code")
    return codes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch a small real-data demo database with the user's own Tushare token."
    )
    parser.add_argument("--stocks", type=stock_codes, required=True, help="逗号分隔 ts_code，如 600519.SH,000001.SZ")
    parser.add_argument("--start", required=True, help="开始日期，YYYYMMDD")
    parser.add_argument("--end", required=True, help="结束日期，YYYYMMDD")
    parser.add_argument("--out", default="data/stock.db", help="输出 SQLite 路径，默认 data/stock.db")
    return parser.parse_args()


def require_tushare_api() -> Any:
    import tushare as ts
    from app.config import TUSHARE_TOKEN

    if not TUSHARE_TOKEN:
        raise SystemExit(
            "Tushare token 未配置。请复制 config/local.toml.example 为 config/local.toml，"
            "填写 [tushare].token 后重试。"
        )
    return ts.pro_api(TUSHARE_TOKEN)


def fetch_stock_basic(pro: Any, codes: list[str]) -> list[dict[str, Any]]:
    from app.models import StockBasic

    fields = "ts_code,name,industry,market,list_date,list_status"
    df = pro.stock_basic(exchange="", list_status="L", fields=fields)
    if df is None or df.empty:
        raise RuntimeError("Tushare stock_basic 返回为空")

    selected = df[df["ts_code"].isin(codes)]
    missing = sorted(set(codes) - set(selected["ts_code"].tolist()))
    if missing:
        raise RuntimeError(f"stock_basic 未找到这些股票：{', '.join(missing)}")

    model_columns = set(StockBasic.__table__.columns.keys())
    return [
        {key: clean_value(row.get(key)) for key in model_columns if key in row.index}
        for _, row in selected.iterrows()
    ]


def fetch_daily_quotes(pro: Any, codes: list[str], start: str, end: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    fields = "ts_code,trade_date,total_mv,turnover_rate"
    for code in codes:
        df_daily = pro.daily(ts_code=code, start_date=start, end_date=end)
        if df_daily is None or df_daily.empty:
            continue
        df_basic = pro.daily_basic(ts_code=code, start_date=start, end_date=end, fields=fields)
        if df_basic is not None and not df_basic.empty:
            df = pd.merge(df_daily, df_basic, on=["ts_code", "trade_date"], how="left")
        else:
            df = df_daily
        df = df.sort_values("trade_date")
        for _, row in df.iterrows():
            rows.append(
                {
                    "ts_code": clean_value(row.get("ts_code")),
                    "trade_date": clean_value(row.get("trade_date")),
                    "open": clean_value(row.get("open")),
                    "high": clean_value(row.get("high")),
                    "low": clean_value(row.get("low")),
                    "close": clean_value(row.get("close")),
                    "vol": clean_value(row.get("vol")),
                    "amount": clean_value(row.get("amount")),
                    "pct_chg": clean_value(row.get("pct_chg")),
                    "total_mv": clean_value(row.get("total_mv")),
                    "turnover_rate": clean_value(row.get("turnover_rate")),
                }
            )
    if not rows:
        raise RuntimeError("指定股票和日期范围未拉到 daily 行情")
    return rows


def calculate_indicator_rows(quote_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from app.services.technical_indicators import calculate_stock_indicators

    result: list[dict[str, Any]] = []
    for code in sorted({row["ts_code"] for row in quote_rows}):
        quotes = [row for row in quote_rows if row["ts_code"] == code]
        quotes.sort(key=lambda row: row["trade_date"])
        indicators, _ = calculate_stock_indicators(quotes)
        result.extend(indicators)
    return result


def replace_seeded_rows(
    db: Session,
    *,
    codes: list[str],
    start: str,
    end: str,
    stock_rows: list[dict[str, Any]],
    quote_rows: list[dict[str, Any]],
    indicator_rows: list[dict[str, Any]],
) -> None:
    from app.models import DailyIndicator, DailyQuote, StockBasic
    from app.services.strategy import init_builtin_strategies
    from app.services.user_config import ensure_default_configs

    for row in stock_rows:
        existing = db.get(StockBasic, row["ts_code"])
        if existing:
            for key, value in row.items():
                setattr(existing, key, value)
        else:
            db.add(StockBasic(**row))

    db.query(DailyQuote).filter(
        DailyQuote.ts_code.in_(codes),
        DailyQuote.trade_date >= start,
        DailyQuote.trade_date <= end,
    ).delete(synchronize_session=False)
    db.query(DailyIndicator).filter(
        DailyIndicator.ts_code.in_(codes),
        DailyIndicator.trade_date >= start,
        DailyIndicator.trade_date <= end,
    ).delete(synchronize_session=False)

    db.execute(DailyQuote.__table__.insert(), quote_rows)
    db.execute(DailyIndicator.__table__.insert(), indicator_rows)
    db.commit()

    init_builtin_strategies(db)
    ensure_default_configs(db)


def print_counts(db: Session, db_path: Path) -> None:
    for table in ("stock_basic", "daily_quote", "daily_indicator", "strategy", "user_config"):
        count = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
        print(f"{table}={count}")
    print(f"out={db_path}")
    print(f"size_bytes={db_path.stat().st_size}")


def main() -> None:
    args = parse_args()
    out_path = resolve_output_path(args.out)

    pro = require_tushare_api()
    prepare_legacy_base_tables(out_path)
    run_alembic_upgrade(out_path)

    stock_rows = fetch_stock_basic(pro, args.stocks)
    quote_rows = fetch_daily_quotes(pro, args.stocks, args.start, args.end)
    indicator_rows = calculate_indicator_rows(quote_rows)

    session_factory = make_session(out_path)
    with session_factory() as db:
        replace_seeded_rows(
            db,
            codes=args.stocks,
            start=args.start,
            end=args.end,
            stock_rows=stock_rows,
            quote_rows=quote_rows,
            indicator_rows=indicator_rows,
        )
        print_counts(db, out_path)


if __name__ == "__main__":
    main()
