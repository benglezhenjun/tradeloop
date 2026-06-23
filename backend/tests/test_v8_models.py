import pytest
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
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


def test_v8_models_create_expected_tables_and_columns():
    eng = make_engine()
    try:
        import app.models  # noqa: F401
        from app.database import Base

        Base.metadata.create_all(bind=eng)

        inspector = inspect(eng)
        tables = set(inspector.get_table_names())
        assert "daily_indicator" in tables
        assert "daily_moneyflow" in tables
        assert "top_list" in tables
        assert "top_list_detail" in tables

        indicator_columns = {column["name"] for column in inspector.get_columns("daily_indicator")}
        assert {"ma5", "macd_dif", "kdj_k", "rsi_6", "boll_upper", "atr_14", "obv"}.issubset(
            indicator_columns
        )

        moneyflow_columns = {column["name"] for column in inspector.get_columns("daily_moneyflow")}
        assert {
            "net_mf_amount",
            "net_mf_vol",
            "net_amount",
            "buy_elg_amount",
            "buy_lg_amount",
        }.issubset(moneyflow_columns)

        top_list_columns = {column["name"] for column in inspector.get_columns("top_list")}
        assert {"id", "ts_code", "trade_date", "reason", "net_amount"}.issubset(top_list_columns)
        top_list_uniques = {tuple(item["column_names"]) for item in inspector.get_unique_constraints("top_list")}
        assert ("ts_code", "trade_date", "reason") in top_list_uniques
        top_list_unique_constraints = inspector.get_unique_constraints("top_list")
        assert any(
            constraint["name"] == "uq_toplist_ts_date_reason"
            and constraint["column_names"] == ["ts_code", "trade_date", "reason"]
            for constraint in top_list_unique_constraints
        )

        top_list_detail_columns = {
            column["name"] for column in inspector.get_columns("top_list_detail")
        }
        assert {"id", "ts_code", "trade_date", "exalter", "net_buy", "side"}.issubset(
            top_list_detail_columns
        )

        financial_columns = {column["name"] for column in inspector.get_columns("stock_financial")}
        assert {
            "profit_dedt",
            "revenue",
            "eps",
            "gross_margin",
            "current_ratio",
            "ocf_to_or",
            "update_flag",
        }.issubset(financial_columns)
        assert len(financial_columns) >= 50
    finally:
        eng.dispose()


def test_v8_models_support_basic_crud():
    eng = make_engine()
    try:
        import app.models  # noqa: F401
        from app.database import Base
        from app.models import DailyIndicator, DailyMoneyflow, StockFinancial, TopList, TopListDetail

        Base.metadata.create_all(bind=eng)
        Session = sessionmaker(bind=eng)
        session = Session()

        session.add(
            DailyIndicator(
                ts_code="600000.SH",
                trade_date="20260407",
                ma5=10.5,
                macd_dif=0.2,
                obv=1200,
            )
        )
        session.add(
            DailyMoneyflow(
                ts_code="600000.SH",
                trade_date="20260407",
                net_mf_amount=12.3,
                net_mf_vol=2.1,
                net_amount=18.5,
                buy_elg_amount=10.0,
                buy_lg_amount=8.0,
            )
        )
        session.add(
            TopList(
                ts_code="600000.SH",
                trade_date="20260407",
                name="浦发银行",
                net_amount=123.4,
                reason="日涨幅偏离值达7%",
            )
        )
        session.add(
            TopListDetail(
                ts_code="600000.SH",
                trade_date="20260407",
                exalter="机构专用",
                buy=100.0,
                sell=10.0,
                net_buy=90.0,
                side="买入",
                reason="日涨幅偏离值达7%",
            )
        )
        session.add(
            StockFinancial(
                ts_code="600000.SH",
                ann_date="20260331",
                end_date="20251231",
                profit_dedt=1000000.0,
                revenue=2000000.0,
                eps=1.23,
                gross_margin=32.1,
                current_ratio=1.8,
                ocf_to_or=0.7,
                update_flag="1",
            )
        )
        session.commit()

        indicator = session.get(DailyIndicator, ("600000.SH", "20260407"))
        moneyflow = session.get(DailyMoneyflow, ("600000.SH", "20260407"))
        financial = session.get(StockFinancial, ("600000.SH", "20260331", "20251231"))
        toplist = session.query(TopList).filter_by(ts_code="600000.SH").one()
        toplist_detail = session.query(TopListDetail).filter_by(ts_code="600000.SH").one()

        assert indicator is not None and indicator.ma5 == 10.5
        assert moneyflow is not None and moneyflow.net_amount == 18.5
        assert financial is not None and financial.eps == 1.23
        assert toplist.reason == "日涨幅偏离值达7%"
        assert toplist_detail.net_buy == 90.0
    finally:
        eng.dispose()


def test_top_list_rejects_duplicate_ts_date_reason():
    eng = make_engine()
    try:
        import app.models  # noqa: F401
        from app.database import Base
        from app.models import TopList

        Base.metadata.create_all(bind=eng)
        Session = sessionmaker(bind=eng)
        session = Session()

        session.add(TopList(ts_code="600000.SH", trade_date="20260407", reason="deviation"))
        session.commit()

        session.add(TopList(ts_code="600000.SH", trade_date="20260407", reason="deviation"))
        with pytest.raises(IntegrityError):
            session.commit()
    finally:
        eng.dispose()
