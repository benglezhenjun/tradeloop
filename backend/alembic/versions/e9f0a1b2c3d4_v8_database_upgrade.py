"""v8 database upgrade

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
Create Date: 2026-04-07 23:30:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "e9f0a1b2c3d4"
down_revision: Union[str, Sequence[str], None] = "d8e9f0a1b2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_stock_financial_full() -> None:
    op.create_table(
        "stock_financial",
        sa.Column("ts_code", sa.String(length=20), nullable=False),
        sa.Column("ann_date", sa.String(length=8), nullable=False),
        sa.Column("end_date", sa.String(length=8), nullable=False),
        sa.Column("eps", sa.Float(), nullable=True),
        sa.Column("dt_eps", sa.Float(), nullable=True),
        sa.Column("total_revenue_ps", sa.Float(), nullable=True),
        sa.Column("revenue_ps", sa.Float(), nullable=True),
        sa.Column("capital_rese_ps", sa.Float(), nullable=True),
        sa.Column("surplus_rese_ps", sa.Float(), nullable=True),
        sa.Column("undist_profit_ps", sa.Float(), nullable=True),
        sa.Column("bps", sa.Float(), nullable=True),
        sa.Column("ocfps", sa.Float(), nullable=True),
        sa.Column("retainedps", sa.Float(), nullable=True),
        sa.Column("cfps", sa.Float(), nullable=True),
        sa.Column("ebit_ps", sa.Float(), nullable=True),
        sa.Column("fcff_ps", sa.Float(), nullable=True),
        sa.Column("fcfe_ps", sa.Float(), nullable=True),
        sa.Column("diluted2_eps", sa.Float(), nullable=True),
        sa.Column("profit_dedt", sa.Float(), nullable=True),
        sa.Column("revenue", sa.Float(), nullable=True),
        sa.Column("extra_item", sa.Float(), nullable=True),
        sa.Column("gross_margin", sa.Float(), nullable=True),
        sa.Column("op_income", sa.Float(), nullable=True),
        sa.Column("valuechange_income", sa.Float(), nullable=True),
        sa.Column("interst_income", sa.Float(), nullable=True),
        sa.Column("daa", sa.Float(), nullable=True),
        sa.Column("ebit", sa.Float(), nullable=True),
        sa.Column("ebitda", sa.Float(), nullable=True),
        sa.Column("fcff", sa.Float(), nullable=True),
        sa.Column("fcfe", sa.Float(), nullable=True),
        sa.Column("retained_earnings", sa.Float(), nullable=True),
        sa.Column("netprofit_margin", sa.Float(), nullable=True),
        sa.Column("grossprofit_margin", sa.Float(), nullable=True),
        sa.Column("cogs_of_sales", sa.Float(), nullable=True),
        sa.Column("expense_of_sales", sa.Float(), nullable=True),
        sa.Column("profit_to_gr", sa.Float(), nullable=True),
        sa.Column("saleexp_to_gr", sa.Float(), nullable=True),
        sa.Column("adminexp_to_gr", sa.Float(), nullable=True),
        sa.Column("finaexp_to_gr", sa.Float(), nullable=True),
        sa.Column("impai_ttm", sa.Float(), nullable=True),
        sa.Column("gc_of_gr", sa.Float(), nullable=True),
        sa.Column("op_of_gr", sa.Float(), nullable=True),
        sa.Column("ebit_of_gr", sa.Float(), nullable=True),
        sa.Column("roe", sa.Float(), nullable=True),
        sa.Column("roe_waa", sa.Float(), nullable=True),
        sa.Column("roe_dt", sa.Float(), nullable=True),
        sa.Column("roa", sa.Float(), nullable=True),
        sa.Column("npta", sa.Float(), nullable=True),
        sa.Column("roic", sa.Float(), nullable=True),
        sa.Column("roe_yearly", sa.Float(), nullable=True),
        sa.Column("roa2_yearly", sa.Float(), nullable=True),
        sa.Column("roe_avg", sa.Float(), nullable=True),
        sa.Column("opincome_of_ebt", sa.Float(), nullable=True),
        sa.Column("investincome_of_ebt", sa.Float(), nullable=True),
        sa.Column("n_op_profit_of_ebt", sa.Float(), nullable=True),
        sa.Column("tax_to_ebt", sa.Float(), nullable=True),
        sa.Column("dtprofit_to_profit", sa.Float(), nullable=True),
        sa.Column("invturn_days", sa.Float(), nullable=True),
        sa.Column("arturn_days", sa.Float(), nullable=True),
        sa.Column("inv_turn", sa.Float(), nullable=True),
        sa.Column("ar_turn", sa.Float(), nullable=True),
        sa.Column("ca_turn", sa.Float(), nullable=True),
        sa.Column("fa_turn", sa.Float(), nullable=True),
        sa.Column("assets_turn", sa.Float(), nullable=True),
        sa.Column("current_ratio", sa.Float(), nullable=True),
        sa.Column("quick_ratio", sa.Float(), nullable=True),
        sa.Column("cash_ratio", sa.Float(), nullable=True),
        sa.Column("debt_to_assets", sa.Float(), nullable=True),
        sa.Column("assets_to_eqt", sa.Float(), nullable=True),
        sa.Column("dp_assets_to_eqt", sa.Float(), nullable=True),
        sa.Column("ca_to_assets", sa.Float(), nullable=True),
        sa.Column("nca_to_assets", sa.Float(), nullable=True),
        sa.Column("tbassets_to_totalassets", sa.Float(), nullable=True),
        sa.Column("int_to_talcap", sa.Float(), nullable=True),
        sa.Column("eqt_to_talcap", sa.Float(), nullable=True),
        sa.Column("currentdebt_to_debt", sa.Float(), nullable=True),
        sa.Column("longdeb_to_debt", sa.Float(), nullable=True),
        sa.Column("ocf_to_shortdebt", sa.Float(), nullable=True),
        sa.Column("eqt_to_debt", sa.Float(), nullable=True),
        sa.Column("eqt_to_interestdebt", sa.Float(), nullable=True),
        sa.Column("tangibleasset_to_debt", sa.Float(), nullable=True),
        sa.Column("tangibleasset_to_netdebt", sa.Float(), nullable=True),
        sa.Column("ocf_to_debt", sa.Float(), nullable=True),
        sa.Column("ocf_to_interestdebt", sa.Float(), nullable=True),
        sa.Column("ocf_to_capitalexp", sa.Float(), nullable=True),
        sa.Column("cash_to_currentliab", sa.Float(), nullable=True),
        sa.Column("current_exint", sa.Float(), nullable=True),
        sa.Column("noncurrent_exint", sa.Float(), nullable=True),
        sa.Column("interestdebt", sa.Float(), nullable=True),
        sa.Column("netdebt", sa.Float(), nullable=True),
        sa.Column("tangible_asset", sa.Float(), nullable=True),
        sa.Column("working_capital", sa.Float(), nullable=True),
        sa.Column("networking_capital", sa.Float(), nullable=True),
        sa.Column("invest_capital", sa.Float(), nullable=True),
        sa.Column("salescash_to_or", sa.Float(), nullable=True),
        sa.Column("ocf_to_or", sa.Float(), nullable=True),
        sa.Column("ocf_to_opincome", sa.Float(), nullable=True),
        sa.Column("capitalized_to_da", sa.Float(), nullable=True),
        sa.Column("update_flag", sa.String(length=1), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("ts_code", "ann_date", "end_date"),
    )
    op.create_index("ix_financial_code", "stock_financial", ["ts_code"], unique=False)
    op.create_index("ix_financial_end_date", "stock_financial", ["end_date"], unique=False)


def _create_stock_financial_old() -> None:
    op.create_table(
        "stock_financial",
        sa.Column("ts_code", sa.String(length=20), nullable=False),
        sa.Column("ann_date", sa.String(length=8), nullable=False),
        sa.Column("end_date", sa.String(length=8), nullable=False),
        sa.Column("profit_dedt", sa.Float(), nullable=True),
        sa.Column("revenue", sa.Float(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("ts_code", "ann_date", "end_date"),
    )
    op.create_index("ix_financial_code", "stock_financial", ["ts_code"], unique=False)
    op.create_index("ix_financial_end_date", "stock_financial", ["end_date"], unique=False)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    op.create_table(
        "daily_indicator",
        sa.Column("ts_code", sa.String(length=20), nullable=False),
        sa.Column("trade_date", sa.String(length=8), nullable=False),
        sa.Column("ma5", sa.Float(), nullable=True),
        sa.Column("ma10", sa.Float(), nullable=True),
        sa.Column("ma20", sa.Float(), nullable=True),
        sa.Column("ma60", sa.Float(), nullable=True),
        sa.Column("ma120", sa.Float(), nullable=True),
        sa.Column("ma240", sa.Float(), nullable=True),
        sa.Column("macd_dif", sa.Float(), nullable=True),
        sa.Column("macd_dea", sa.Float(), nullable=True),
        sa.Column("macd_hist", sa.Float(), nullable=True),
        sa.Column("kdj_k", sa.Float(), nullable=True),
        sa.Column("kdj_d", sa.Float(), nullable=True),
        sa.Column("kdj_j", sa.Float(), nullable=True),
        sa.Column("rsi_6", sa.Float(), nullable=True),
        sa.Column("rsi_12", sa.Float(), nullable=True),
        sa.Column("rsi_24", sa.Float(), nullable=True),
        sa.Column("boll_upper", sa.Float(), nullable=True),
        sa.Column("boll_mid", sa.Float(), nullable=True),
        sa.Column("boll_lower", sa.Float(), nullable=True),
        sa.Column("atr_14", sa.Float(), nullable=True),
        sa.Column("obv", sa.Float(), nullable=True),
        sa.Column("volume_ratio", sa.Float(), nullable=True),
        sa.Column("turnover_change", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("ts_code", "trade_date"),
    )
    op.create_index("ix_indicator_trade_date", "daily_indicator", ["trade_date"], unique=False)
    op.create_index("ix_indicator_code_date", "daily_indicator", ["ts_code", "trade_date"], unique=False)

    op.create_table(
        "daily_moneyflow",
        sa.Column("ts_code", sa.String(length=20), nullable=False),
        sa.Column("trade_date", sa.String(length=8), nullable=False),
        sa.Column("net_mf_amount", sa.Float(), nullable=True),
        sa.Column("net_mf_vol", sa.Float(), nullable=True),
        sa.Column("net_amount", sa.Float(), nullable=True),
        sa.Column("buy_elg_amount", sa.Float(), nullable=True),
        sa.Column("buy_lg_amount", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("ts_code", "trade_date"),
    )
    op.create_index("ix_moneyflow_trade_date", "daily_moneyflow", ["trade_date"], unique=False)
    op.create_index("ix_moneyflow_code_date", "daily_moneyflow", ["ts_code", "trade_date"], unique=False)

    op.create_table(
        "top_list",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ts_code", sa.String(length=20), nullable=False),
        sa.Column("trade_date", sa.String(length=8), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=True),
        sa.Column("close", sa.Float(), nullable=True),
        sa.Column("pct_change", sa.Float(), nullable=True),
        sa.Column("turnover_rate", sa.Float(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("l_buy", sa.Float(), nullable=True),
        sa.Column("l_sell", sa.Float(), nullable=True),
        sa.Column("net_amount", sa.Float(), nullable=True),
        sa.Column("net_rate", sa.Float(), nullable=True),
        sa.Column("amount_rate", sa.Float(), nullable=True),
        sa.Column("float_values", sa.Float(), nullable=True),
        sa.Column("reason", sa.String(length=200), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_top_list_trade_date", "top_list", ["trade_date"], unique=False)
    op.create_index("ix_top_list_code_date", "top_list", ["ts_code", "trade_date"], unique=False)

    op.create_table(
        "top_list_detail",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ts_code", sa.String(length=20), nullable=False),
        sa.Column("trade_date", sa.String(length=8), nullable=False),
        sa.Column("exalter", sa.String(length=200), nullable=True),
        sa.Column("buy", sa.Float(), nullable=True),
        sa.Column("sell", sa.Float(), nullable=True),
        sa.Column("net_buy", sa.Float(), nullable=True),
        sa.Column("side", sa.String(length=10), nullable=True),
        sa.Column("reason", sa.String(length=200), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_top_list_detail_trade_date",
        "top_list_detail",
        ["trade_date"],
        unique=False,
    )
    op.create_index(
        "ix_top_list_detail_code_date",
        "top_list_detail",
        ["ts_code", "trade_date"],
        unique=False,
    )

    if "stock_financial" in inspector.get_table_names():
        financial_indexes = {item["name"] for item in inspector.get_indexes("stock_financial")}
        if "ix_financial_end_date" in financial_indexes:
            op.drop_index("ix_financial_end_date", table_name="stock_financial")
        if "ix_financial_code" in financial_indexes:
            op.drop_index("ix_financial_code", table_name="stock_financial")
        op.drop_table("stock_financial")
    _create_stock_financial_full()


def downgrade() -> None:
    op.drop_index("ix_financial_end_date", table_name="stock_financial")
    op.drop_index("ix_financial_code", table_name="stock_financial")
    op.drop_table("stock_financial")
    _create_stock_financial_old()

    op.drop_index("ix_top_list_detail_code_date", table_name="top_list_detail")
    op.drop_index("ix_top_list_detail_trade_date", table_name="top_list_detail")
    op.drop_table("top_list_detail")

    op.drop_index("ix_top_list_code_date", table_name="top_list")
    op.drop_index("ix_top_list_trade_date", table_name="top_list")
    op.drop_table("top_list")

    op.drop_index("ix_moneyflow_code_date", table_name="daily_moneyflow")
    op.drop_index("ix_moneyflow_trade_date", table_name="daily_moneyflow")
    op.drop_table("daily_moneyflow")

    op.drop_index("ix_indicator_code_date", table_name="daily_indicator")
    op.drop_index("ix_indicator_trade_date", table_name="daily_indicator")
    op.drop_table("daily_indicator")
