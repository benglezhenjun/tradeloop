"""Generate a deterministic synthetic demo database for TradeLoop.

The generated data is fictional and must not be used for investment decisions.
It never calls Tushare or any other market data provider.
"""

from __future__ import annotations

import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
DATA_DIR = PROJECT_ROOT / "data"
SAMPLE_DB = DATA_DIR / "sample.db"
MAX_DB_BYTES = 20 * 1024 * 1024
RANDOM_SEED = 20260101
FIXED_DATETIME = "2026-06-19 15:00:00"
FIXED_ISO_DATETIME = "2026-06-19T15:00:00Z"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


STOCKS = [
    {"ts_code": "600901.SH", "name": "示例科技一号", "industry": "科技", "market": "主板", "list_date": "20150108", "base": 34.0, "shares": 1_850_000_000},
    {"ts_code": "600902.SH", "name": "虚构银行二号", "industry": "金融", "market": "主板", "list_date": "20120618", "base": 9.2, "shares": 5_600_000_000},
    {"ts_code": "600903.SH", "name": "演示消费三号", "industry": "消费", "market": "主板", "list_date": "20180820", "base": 22.0, "shares": 1_250_000_000},
    {"ts_code": "000901.SZ", "name": "样例制造四号", "industry": "制造", "market": "主板", "list_date": "20140312", "base": 14.0, "shares": 1_600_000_000},
    {"ts_code": "000902.SZ", "name": "虚拟能源五号", "industry": "新能源", "market": "主板", "list_date": "20170707", "base": 18.0, "shares": 980_000_000},
    {"ts_code": "000903.SZ", "name": "示范医药六号", "industry": "医药", "market": "主板", "list_date": "20190919", "base": 28.0, "shares": 760_000_000},
    {"ts_code": "300901.SZ", "name": "演示软件七号", "industry": "科技", "market": "创业板", "list_date": "20200115", "base": 42.0, "shares": 520_000_000},
    {"ts_code": "300902.SZ", "name": "虚构装备八号", "industry": "高端装备", "market": "创业板", "list_date": "20210422", "base": 31.0, "shares": 430_000_000},
    {"ts_code": "300903.SZ", "name": "样例传媒九号", "industry": "传媒", "market": "创业板", "list_date": "20220510", "base": 16.5, "shares": 360_000_000},
    {"ts_code": "688901.SH", "name": "示例芯片十号", "industry": "半导体", "market": "科创板", "list_date": "20201111", "base": 58.0, "shares": 310_000_000},
    {"ts_code": "688902.SH", "name": "虚拟机器人十一号", "industry": "机器人", "market": "科创板", "list_date": "20211224", "base": 46.0, "shares": 280_000_000},
    {"ts_code": "688903.SH", "name": "演示材料十二号", "industry": "新材料", "market": "科创板", "list_date": "20230303", "base": 38.0, "shares": 260_000_000},
]

THEMES = [
    ("DEMO_AI", "虚构AI应用"),
    ("DEMO_EV", "演示新能源"),
    ("DEMO_MED", "样例创新药"),
    ("DEMO_CHIP", "示例半导体"),
]


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.resolve().as_posix()}"


def reset_database_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    for suffix in ("", "-journal", "-shm", "-wal"):
        candidate = Path(f"{path}{suffix}")
        if candidate.exists():
            candidate.unlink()


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


def business_dates(*, end: date, count: int) -> list[str]:
    result: list[str] = []
    current = end
    while len(result) < count:
        if current.weekday() < 5:
            result.append(current.strftime("%Y%m%d"))
        current -= timedelta(days=1)
    return list(reversed(result))


def rounded(value: float, digits: int = 4) -> float:
    return round(float(value), digits)


def generate_stock_rows() -> list[dict[str, Any]]:
    return [
        {
            "ts_code": stock["ts_code"],
            "name": stock["name"],
            "industry": stock["industry"],
            "market": stock["market"],
            "list_date": stock["list_date"],
            "list_status": "L",
        }
        for stock in STOCKS
    ]


def generate_quote_rows(trade_dates: list[str], rng: random.Random) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for stock_index, stock in enumerate(STOCKS):
        close = float(stock["base"])
        shares = int(stock["shares"])
        drift = 0.00045 if stock_index < 6 else 0.00015

        for idx, trade_date in enumerate(trade_dates):
            prev_close = close
            daily_return = max(min(rng.gauss(drift, 0.015), 0.095), -0.095)
            close = max(2.0, prev_close * (1 + daily_return))
            open_price = max(1.0, prev_close * (1 + rng.gauss(0, 0.006)))
            high = max(open_price, close) * (1 + abs(rng.gauss(0.006, 0.004)))
            low = min(open_price, close) * (1 - abs(rng.gauss(0.006, 0.004)))
            low = max(0.5, low)
            turnover_rate = max(0.25, min(12.0, rng.lognormvariate(0.5, 0.45)))
            if idx % 37 == 0:
                turnover_rate *= 1.8
            vol = shares * turnover_rate / 100 / 100
            avg_price = (open_price + high + low + close) / 4
            amount = avg_price * vol * 100 / 1000
            pct_chg = 0.0 if idx == 0 else (close - prev_close) / prev_close * 100
            rows.append(
                {
                    "ts_code": stock["ts_code"],
                    "trade_date": trade_date,
                    "open": rounded(open_price),
                    "high": rounded(high),
                    "low": rounded(low),
                    "close": rounded(close),
                    "vol": rounded(vol, 2),
                    "amount": rounded(amount, 2),
                    "pct_chg": rounded(pct_chg),
                    "total_mv": rounded(close * shares / 10_000, 2),
                    "turnover_rate": rounded(turnover_rate),
                }
            )
    return rows


def generate_indicator_rows(quote_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from app.services.technical_indicators import calculate_stock_indicators

    result: list[dict[str, Any]] = []
    for stock in STOCKS:
        quotes = [row for row in quote_rows if row["ts_code"] == stock["ts_code"]]
        quotes.sort(key=lambda row: row["trade_date"])
        indicator_rows, _ = calculate_stock_indicators(quotes)
        result.extend(indicator_rows)
    return result


def generate_financial_rows(rng: random.Random) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for stock_index, stock in enumerate(STOCKS):
        base_revenue = rng.uniform(1.6e9, 32e9)
        base_profit = base_revenue * rng.uniform(0.055, 0.16)
        for offset, year in enumerate((2023, 2024, 2025)):
            if stock_index < 7:
                growth = 1 + offset * rng.uniform(0.12, 0.22)
            else:
                growth = 1 + offset * rng.uniform(-0.04, 0.08)
            revenue = base_revenue * growth
            profit = base_profit * growth * rng.uniform(0.96, 1.08)
            rows.append(
                {
                    "ts_code": stock["ts_code"],
                    "ann_date": f"{year + 1}0430",
                    "end_date": f"{year}1231",
                    "profit_dedt": rounded(profit, 2),
                    "revenue": rounded(revenue, 2),
                    "eps": rounded(profit / int(stock["shares"]), 4),
                    "roe": rounded(rng.uniform(7.5, 21.0), 4),
                    "gross_margin": rounded(rng.uniform(18.0, 54.0), 4),
                    "debt_to_assets": rounded(rng.uniform(22.0, 66.0), 4),
                    "update_flag": "0",
                }
            )
    return rows


def generate_limit_event_rows(trade_dates: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    sentiment_dates = trade_dates[-90:]
    for idx, trade_date in enumerate(sentiment_dates):
        specs = [
            (STOCKS[0], "U", min(5, 1 + idx % 5)),
            (STOCKS[1], "U", min(4, 1 + (idx + 1) % 4)),
            (STOCKS[(idx % 9) + 2], "U", 1 + idx % 2),
            (STOCKS[(idx % 6) + 5], "Z", 1 + idx % 3),
            (STOCKS[(idx % 5) + 7], "D", 1),
        ]
        seen: set[tuple[str, str]] = set()
        for stock, limit_type, limit_times in specs:
            key = (str(stock["ts_code"]), limit_type)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "ts_code": stock["ts_code"],
                    "trade_date": trade_date,
                    "limit_type": limit_type,
                    "name": stock["name"],
                    "limit_times": limit_times,
                    "up_stat": f"{limit_times}天{limit_times}板" if limit_type == "U" else "演示事件",
                    "first_time": "09:45:00",
                    "last_time": "14:35:00",
                    "open_num": idx % 3,
                    "fd_amount": rounded(20_000 + idx * 1500 + limit_times * 10_000, 2),
                    "source": "synthetic",
                }
            )
    return rows


def generate_theme_heat_rows(trade_dates: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    sentiment_dates = trade_dates[-90:]
    for idx, trade_date in enumerate(sentiment_dates):
        leader_offset = idx // 18 % len(THEMES)
        ranked_themes = THEMES[leader_offset:] + THEMES[:leader_offset]
        for rank, (theme_code, theme_name) in enumerate(ranked_themes, start=1):
            rows.append(
                {
                    "theme_code": theme_code,
                    "trade_date": trade_date,
                    "theme_name": theme_name,
                    "rank": rank,
                    "up_nums": max(1, 12 - rank * 2 + idx % 4),
                    "cons_nums": max(1, 5 - rank + idx % 2),
                    "up_stat": f"{max(1, 12 - rank * 2)}家上涨",
                    "score": rounded(93 - rank * 7 + (idx % 5) * 0.8),
                    "source": "synthetic",
                }
            )
    return rows


def generate_moneyflow_rows(quote_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected_codes = {stock["ts_code"] for stock in STOCKS[:8]}
    selected_dates = sorted({row["trade_date"] for row in quote_rows})[-60:]
    selected_date_set = set(selected_dates)
    rows: list[dict[str, Any]] = []
    for row in quote_rows:
        if row["ts_code"] not in selected_codes or row["trade_date"] not in selected_date_set:
            continue
        net_amount = float(row["amount"]) * (float(row["pct_chg"]) / 100) * 0.12
        rows.append(
            {
                "ts_code": row["ts_code"],
                "trade_date": row["trade_date"],
                "net_mf_amount": rounded(net_amount, 2),
                "net_mf_vol": rounded(net_amount / max(float(row["close"]), 1) * 10, 2),
                "net_amount": rounded(net_amount, 2),
                "buy_elg_amount": rounded(abs(net_amount) * 0.55, 2),
                "buy_lg_amount": rounded(abs(net_amount) * 0.35, 2),
            }
        )
    return rows


def insert_static_demo_data(db: Session, trade_dates: list[str], quote_rows: list[dict[str, Any]]) -> None:
    from app.models import TradeRecord, WatchlistGroup, WatchlistStock
    from app.services.position import recalculate_position
    from app.services.strategy import init_builtin_strategies
    from app.services.user_config import ensure_default_configs

    group = WatchlistGroup(name="演示分组", description="合成样例库自选股", sort_order=1)
    db.add(group)
    db.flush()
    for stock in STOCKS[:5]:
        db.add(WatchlistStock(group_id=group.id, ts_code=stock["ts_code"], note="样例关注标的"))

    init_builtin_strategies(db)
    ensure_default_configs(db)

    quote_by_key = {(row["ts_code"], row["trade_date"]): row for row in quote_rows}
    trade_stock = STOCKS[0]
    trade_dates_for_position = [trade_dates[80], trade_dates[120], trade_dates[170]]
    trade_specs = [
        ("buy", 1000, trade_dates_for_position[0], "首次演示买入"),
        ("buy", 500, trade_dates_for_position[1], "回踩加仓"),
        ("sell", 600, trade_dates_for_position[2], "部分止盈"),
    ]
    for direction, quantity, trade_date, note in trade_specs:
        quote = quote_by_key[(trade_stock["ts_code"], trade_date)]
        price = float(quote["close"])
        amount = rounded(price * quantity, 2)
        fee = rounded(amount * (0.00125 if direction == "sell" else 0.00025), 2)
        db.add(
            TradeRecord(
                ts_code=trade_stock["ts_code"],
                stock_name=trade_stock["name"],
                direction=direction,
                price=price,
                quantity=quantity,
                amount=amount,
                fee=fee,
                trade_date=datetime.strptime(trade_date, "%Y%m%d").strftime("%Y-%m-%d"),
                trade_time="10:15:00",
                note=note,
                created_at=FIXED_ISO_DATETIME,
            )
        )
    db.commit()
    recalculate_position(db, trade_stock["ts_code"])


def normalize_demo_timestamps(db: Session) -> None:
    datetime_tables = [
        ("stock_basic", "updated_at", FIXED_DATETIME),
        ("stock_financial", "updated_at", FIXED_DATETIME),
        ("watchlist_group", "created_at", FIXED_DATETIME),
        ("watchlist_stock", "added_at", FIXED_DATETIME),
        ("strategy", "created_at", FIXED_DATETIME),
        ("strategy", "updated_at", FIXED_DATETIME),
    ]
    text_tables = [
        ("trade_record", "created_at", FIXED_ISO_DATETIME),
        ("position", "updated_at", FIXED_ISO_DATETIME),
    ]
    for table, column, value in datetime_tables + text_tables:
        db.execute(text(f"UPDATE {table} SET {column} = :value"), {"value": value})
    db.commit()


def normalize_index_order(db: Session) -> None:
    statements = [
        "DROP INDEX IF EXISTS ix_daily_trade_date",
        "DROP INDEX IF EXISTS ix_daily_code_date",
        "CREATE INDEX ix_daily_trade_date ON daily_quote (trade_date)",
        "CREATE INDEX ix_daily_code_date ON daily_quote (ts_code, trade_date)",
        "DROP INDEX IF EXISTS ix_top_list_trade_date",
        "DROP INDEX IF EXISTS ix_top_list_code_date",
        "CREATE INDEX ix_top_list_trade_date ON top_list (trade_date)",
        "CREATE INDEX ix_top_list_code_date ON top_list (ts_code, trade_date)",
        "DROP INDEX IF EXISTS ix_top_list_detail_trade_date",
        "DROP INDEX IF EXISTS ix_top_list_detail_code_date",
        "CREATE INDEX ix_top_list_detail_trade_date ON top_list_detail (trade_date)",
        "CREATE INDEX ix_top_list_detail_code_date ON top_list_detail (ts_code, trade_date)",
    ]
    for statement in statements:
        db.execute(text(statement))
    db.commit()


def count_table(db: Session, table_name: str) -> int:
    return int(db.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar_one())


def collect_counts(db: Session) -> dict[str, int]:
    tables = [
        "stock_basic",
        "daily_quote",
        "daily_indicator",
        "stock_financial",
        "limit_event_daily",
        "theme_heat_daily",
        "market_sentiment_daily",
        "watchlist_group",
        "watchlist_stock",
        "strategy",
        "daily_moneyflow",
        "trade_record",
        "position",
    ]
    return {table: count_table(db, table) for table in tables}


def assert_acceptance(db_path: Path, counts: dict[str, int]) -> None:
    size = db_path.stat().st_size
    if size >= MAX_DB_BYTES:
        raise RuntimeError(f"sample.db too large: {size} bytes")

    expected = {
        "stock_basic": 12,
        "daily_quote": 3001,
        "daily_indicator": 1,
        "stock_financial": 1,
        "market_sentiment_daily": 1,
        "watchlist_group": 1,
        "watchlist_stock": 5,
        "strategy": 2,
    }
    failed = [
        f"{table}={counts.get(table, 0)} < {minimum}"
        for table, minimum in expected.items()
        if counts.get(table, 0) < minimum
    ]
    if failed:
        raise RuntimeError("sample.db acceptance check failed: " + "; ".join(failed))


def main() -> None:
    from app.models import (
        DailyIndicator,
        DailyMoneyflow,
        DailyQuote,
        LimitEventDaily,
        StockBasic,
        StockFinancial,
        ThemeHeatDaily,
    )
    from app.services.market_sentiment import sync_market_sentiment_daily

    rng = random.Random(RANDOM_SEED)
    reset_database_file(SAMPLE_DB)
    prepare_legacy_base_tables(SAMPLE_DB)
    run_alembic_upgrade(SAMPLE_DB)

    session_factory = make_session(SAMPLE_DB)
    trade_dates = business_dates(end=date(2026, 6, 19), count=280)
    quote_rows = generate_quote_rows(trade_dates, rng)

    with session_factory() as db:
        db.execute(StockBasic.__table__.insert(), generate_stock_rows())
        db.execute(DailyQuote.__table__.insert(), quote_rows)
        db.execute(DailyIndicator.__table__.insert(), generate_indicator_rows(quote_rows))
        db.execute(StockFinancial.__table__.insert(), generate_financial_rows(rng))
        db.execute(LimitEventDaily.__table__.insert(), generate_limit_event_rows(trade_dates))
        db.execute(ThemeHeatDaily.__table__.insert(), generate_theme_heat_rows(trade_dates))
        db.execute(DailyMoneyflow.__table__.insert(), generate_moneyflow_rows(quote_rows))
        db.commit()

        sync_market_sentiment_daily(db, trade_dates[-90:])
        insert_static_demo_data(db, trade_dates, quote_rows)
        normalize_demo_timestamps(db)
        normalize_index_order(db)
        counts = collect_counts(db)
        alembic_version = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one()

    assert_acceptance(SAMPLE_DB, counts)
    print(f"generated={SAMPLE_DB}")
    print(f"size_bytes={SAMPLE_DB.stat().st_size}")
    print(f"alembic_version={alembic_version}")
    for table, count in counts.items():
        print(f"{table}={count}")


if __name__ == "__main__":
    main()
