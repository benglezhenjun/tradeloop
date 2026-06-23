"""
V3 Dashboard market stats tests.

Covers:
- get_market_overview: 有数据、无数据、涨停阈值（主板/科创板/创业板）
- get_industry_heat: 行业聚合、排序、NULL行业过滤
- get_breadth_history: 天数限制、日期升序
"""

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(eng, "connect")
    def _set_pragma(dbapi_connection, _):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    import app.models  # noqa: F401 — ensures all tables are registered
    from app.database import Base

    Base.metadata.create_all(bind=eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def insert_stock(db, ts_code: str, industry: str | None = "银行", market: str = "主板"):
    db.execute(
        text(
            "INSERT OR IGNORE INTO stock_basic "
            "(ts_code, name, industry, market, list_date, list_status) "
            "VALUES (:ts_code, :name, :industry, :market, '20200101', 'L')"
        ),
        {"ts_code": ts_code, "name": ts_code, "industry": industry, "market": market},
    )
    db.commit()


def insert_quote(db, ts_code: str, trade_date: str, pct_chg: float, amount: float = 100_000.0):
    db.execute(
        text(
            "INSERT OR IGNORE INTO daily_quote "
            "(ts_code, trade_date, open, high, low, close, vol, amount, pct_chg, total_mv, turnover_rate) "
            "VALUES (:ts_code, :trade_date, 10, 11, 9, 10, 1000, :amount, :pct_chg, 500000, 1.0)"
        ),
        {"ts_code": ts_code, "trade_date": trade_date, "amount": amount, "pct_chg": pct_chg},
    )
    db.commit()


# ---------------------------------------------------------------------------
# get_market_overview
# ---------------------------------------------------------------------------

class TestMarketOverview:
    def test_empty_database_returns_null_trade_date(self, db):
        from app.services.market import get_market_overview
        result = get_market_overview(db)
        assert result["trade_date"] is None
        assert result["up_count"] == 0
        assert result["down_count"] == 0
        assert result["limit_up_count"] == 0

    def test_basic_counts(self, db):
        from app.services.market import get_market_overview

        insert_stock(db, "000001.SZ")
        insert_stock(db, "000002.SZ")
        insert_stock(db, "000003.SZ")

        insert_quote(db, "000001.SZ", "20260401", pct_chg=2.0)   # up
        insert_quote(db, "000002.SZ", "20260401", pct_chg=-1.5)  # down
        insert_quote(db, "000003.SZ", "20260401", pct_chg=0.0)   # flat

        result = get_market_overview(db)
        assert result["trade_date"] == "20260401"
        assert result["up_count"] == 1
        assert result["down_count"] == 1
        assert result["flat_count"] == 1

    def test_limit_up_mainboard_threshold(self, db):
        """主板涨停阈值 9.9%"""
        from app.services.market import get_market_overview

        insert_stock(db, "000001.SZ")
        insert_stock(db, "000002.SZ")

        insert_quote(db, "000001.SZ", "20260401", pct_chg=9.9)   # 涨停
        insert_quote(db, "000002.SZ", "20260401", pct_chg=9.8)   # 未涨停

        result = get_market_overview(db)
        assert result["limit_up_count"] == 1

    def test_limit_down_mainboard_threshold(self, db):
        """主板跌停阈值 -9.9%"""
        from app.services.market import get_market_overview

        insert_stock(db, "000001.SZ")
        insert_stock(db, "000002.SZ")

        insert_quote(db, "000001.SZ", "20260401", pct_chg=-9.9)  # 跌停
        insert_quote(db, "000002.SZ", "20260401", pct_chg=-9.8)  # 未跌停

        result = get_market_overview(db)
        assert result["limit_down_count"] == 1

    def test_limit_up_star_board_threshold(self, db):
        """科创板涨停阈值 19.9%，主板 9.9% 阈值不误判"""
        from app.services.market import get_market_overview

        insert_stock(db, "688001.SH", industry="半导体")
        insert_stock(db, "000001.SZ", industry="银行")

        # 科创板 10% 不算涨停
        insert_quote(db, "688001.SH", "20260401", pct_chg=10.0)
        # 主板 9.9% 算涨停
        insert_quote(db, "000001.SZ", "20260401", pct_chg=9.9)

        result = get_market_overview(db)
        assert result["limit_up_count"] == 1  # 只有主板那只

    def test_limit_up_gem_board_threshold(self, db):
        """创业板涨停阈值 19.9%"""
        from app.services.market import get_market_overview

        insert_stock(db, "300001.SZ", industry="医药")
        insert_stock(db, "301001.SZ", industry="医药")

        insert_quote(db, "300001.SZ", "20260401", pct_chg=19.9)  # 涨停
        insert_quote(db, "301001.SZ", "20260401", pct_chg=15.0)  # 未涨停

        result = get_market_overview(db)
        assert result["limit_up_count"] == 1

    def test_total_amount_unit_conversion(self, db):
        """amount 存储单位千元，返回应为亿元"""
        from app.services.market import get_market_overview

        insert_stock(db, "000001.SZ")
        # amount = 10_000_000 千元 = 100 亿元
        insert_quote(db, "000001.SZ", "20260401", pct_chg=1.0, amount=10_000_000.0)

        result = get_market_overview(db)
        assert result["total_amount_yi"] == pytest.approx(100.0, rel=1e-3)

    def test_auto_picks_latest_trade_date(self, db):
        """trade_date=None 时自动取最新日期"""
        from app.services.market import get_market_overview

        insert_stock(db, "000001.SZ")
        insert_quote(db, "000001.SZ", "20260301", pct_chg=1.0)
        insert_quote(db, "000001.SZ", "20260401", pct_chg=2.0)

        result = get_market_overview(db)
        assert result["trade_date"] == "20260401"


# ---------------------------------------------------------------------------
# get_industry_heat
# ---------------------------------------------------------------------------

class TestIndustryHeat:
    def test_empty_returns_empty_list(self, db):
        from app.services.market import get_industry_heat
        assert get_industry_heat(db) == []

    def test_sorted_by_avg_pct_desc(self, db):
        from app.services.market import get_industry_heat

        insert_stock(db, "000001.SZ", industry="银行")
        insert_stock(db, "000002.SZ", industry="医药")

        insert_quote(db, "000001.SZ", "20260401", pct_chg=1.0)
        insert_quote(db, "000002.SZ", "20260401", pct_chg=3.0)

        result = get_industry_heat(db)
        assert len(result) == 2
        assert result[0]["industry"] == "医药"  # 3.0 > 1.0
        assert result[1]["industry"] == "银行"

    def test_null_industry_excluded(self, db):
        from app.services.market import get_industry_heat

        insert_stock(db, "000001.SZ", industry="银行")
        insert_stock(db, "000002.SZ", industry=None)  # 无行业

        insert_quote(db, "000001.SZ", "20260401", pct_chg=1.0)
        insert_quote(db, "000002.SZ", "20260401", pct_chg=5.0)

        result = get_industry_heat(db)
        assert len(result) == 1
        assert result[0]["industry"] == "银行"

    def test_up_down_count_within_industry(self, db):
        from app.services.market import get_industry_heat

        insert_stock(db, "000001.SZ", industry="银行")
        insert_stock(db, "000002.SZ", industry="银行")
        insert_stock(db, "000003.SZ", industry="银行")

        insert_quote(db, "000001.SZ", "20260401", pct_chg=2.0)
        insert_quote(db, "000002.SZ", "20260401", pct_chg=-1.0)
        insert_quote(db, "000003.SZ", "20260401", pct_chg=0.0)

        result = get_industry_heat(db)
        assert len(result) == 1
        row = result[0]
        assert row["stock_count"] == 3
        assert row["up_count"] == 1
        assert row["down_count"] == 1


# ---------------------------------------------------------------------------
# get_breadth_history
# ---------------------------------------------------------------------------

class TestBreadthHistory:
    def test_empty_returns_empty_list(self, db):
        from app.services.market import get_breadth_history
        assert get_breadth_history(db) == []

    def test_sorted_ascending_by_date(self, db):
        from app.services.market import get_breadth_history

        insert_stock(db, "000001.SZ")
        insert_quote(db, "000001.SZ", "20260301", pct_chg=1.0)
        insert_quote(db, "000001.SZ", "20260401", pct_chg=2.0)

        result = get_breadth_history(db)
        assert result[0]["trade_date"] == "20260301"
        assert result[1]["trade_date"] == "20260401"

    def test_days_limit(self, db):
        from app.services.market import get_breadth_history

        insert_stock(db, "000001.SZ")
        # 插入 5 个不同交易日
        for i in range(1, 6):
            insert_quote(db, "000001.SZ", f"2026040{i}", pct_chg=1.0)

        result = get_breadth_history(db, days=3)
        assert len(result) == 3
        # 应取最近 3 天（升序）
        assert result[-1]["trade_date"] == "20260405"

    def test_count_accuracy(self, db):
        from app.services.market import get_breadth_history

        insert_stock(db, "000001.SZ")
        insert_stock(db, "000002.SZ")
        insert_stock(db, "000003.SZ")

        insert_quote(db, "000001.SZ", "20260401", pct_chg=1.0)   # up
        insert_quote(db, "000002.SZ", "20260401", pct_chg=-1.0)  # down
        insert_quote(db, "000003.SZ", "20260401", pct_chg=0.0)   # flat

        result = get_breadth_history(db)
        assert len(result) == 1
        day = result[0]
        assert day["up_count"] == 1
        assert day["down_count"] == 1
        assert day["flat_count"] == 1
