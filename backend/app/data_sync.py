"""
Tushare 数据同步模块

【学习要点】
- 封装第三方 API 调用，统一处理错误和频率限制
- 数据导入采用"分批拉取 + 批量写入"模式，避免内存溢出和 API 限制
- 用 pandas DataFrame 作为中间格式，因为 Tushare 返回的就是 DataFrame
- upsert 模式：数据已存在就更新，不存在就插入，保证可重复运行

实际项目中，数据同步是最容易出问题的环节：
- 网络超时
- API 频率限制
- 数据格式不一致
- 部分数据缺失
所以这里做了详细的错误处理和日志输出
"""

import time
from datetime import datetime, timedelta

import pandas as pd
import tushare as ts
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import TUSHARE_TOKEN
from app.database import SessionLocal, engine
from app.models import Base, DailyQuote, StockBasic, StockFinancial


def get_tushare_api():
    """
    获取 Tushare API 实例

    【学习要点】
    把 API 初始化封装成函数，而不是直接写在模块顶层，有两个好处：
    1. 延迟初始化：只在真正需要时才创建连接
    2. 可以动态读取配置：如果 token 变了不需要重启
    """
    if not TUSHARE_TOKEN:
        raise ValueError(
            "Tushare token 未配置！\n"
            "请在 app/config.py 中��置 TUSHARE_TOKEN\n"
            "获取方式：注册 tushare.pro → 个人主页 → 接口TOKEN"
        )
    # Pass the token explicitly so stale shell env vars do not override it.
    return ts.pro_api(TUSHARE_TOKEN)


def init_database():
    """
    初始化数据库：根据模型定义创建所有表

    【学习要点】
    create_all 会检查表是否已存在：
    - 不存在 → 创建
    - 已存在 → 跳过（不会删除数据）
    这意味着你可以安全地重复调用
    """
    Base.metadata.create_all(bind=engine)
    print("数据库表创建完成")


def sync_stock_basic():
    """
    同步股票基础信息

    从 Tushare 拉取全市场股票列表，写入 stock_basic 表。
    这是最基础的数据，其他所有数据都依赖股票代码。
    """
    print("\n=== 同步股票基础信息 ===")
    pro = get_tushare_api()

    # 拉取所有上市状态的股票（L=上市中）
    df = pro.stock_basic(
        exchange="",  # 空字符串表示所有交易所
        list_status="L",
        fields="ts_code,name,industry,market,list_date,list_status",
    )
    print(f"获取到 {len(df)} 只上市股票")

    # 写入数据库
    db = SessionLocal()
    try:
        count = 0
        for _, row in df.iterrows():
            # 用 merge 实现 upsert：存在就更新，不存在就插入
            stock = db.get(StockBasic, row["ts_code"])
            if stock:
                stock.name = row["name"]
                stock.industry = row.get("industry")
                stock.market = row.get("market")
                stock.list_date = row.get("list_date")
            else:
                stock = StockBasic(
                    ts_code=row["ts_code"],
                    name=row["name"],
                    industry=row.get("industry"),
                    market=row.get("market"),
                    list_date=row.get("list_date"),
                    list_status=row.get("list_status", "L"),
                )
                db.add(stock)
            count += 1
        db.commit()
        print(f"写入 {count} 条股票基础信息")
    finally:
        db.close()


def sync_daily_quotes(start_date: str, end_date: str):
    """
    同步日线行情数据

    【学习要点 - 为什么按日期拉取而不是按股票拉取？】
    - Tushare 的 daily 接口支持按日期拉取全市场数据
    - 按日期拉：每天 1 次调用，240 个交易日 = 240 次
    - 按股票拉：每只 1 次调用，5000 只股票 = 5000 次
    - 按日期拉更高效，消耗更少的 API 调用次数

    参数：
        start_date: 开始日期，格式 YYYYMMDD
        end_date: 结束日期，格式 YYYYMMDD
    """
    print(f"\n=== 同步日线行情：{start_date} → {end_date} ===")
    pro = get_tushare_api()

    # 获取交易日历，知道哪些天有交易
    trade_cal = pro.trade_cal(
        exchange="SSE", start_date=start_date, end_date=end_date, is_open="1"
    )
    trade_dates = sorted(trade_cal["cal_date"].tolist())
    print(f"共 {len(trade_dates)} 个交易日需要同步")

    db = SessionLocal()
    try:
        for i, date in enumerate(trade_dates):
            try:
                # 拉取当日全市场行情
                df_daily = pro.daily(trade_date=date)
                time.sleep(0.3)  # Tushare 频率限制：每分钟最多 200 次

                # 拉取当日基础指标（总市值、换手率等）
                df_basic = pro.daily_basic(
                    trade_date=date, fields="ts_code,trade_date,total_mv,turnover_rate"
                )
                time.sleep(0.3)

                if df_daily is None or df_daily.empty:
                    continue

                # 合并两个 DataFrame
                # 【学习要点】merge 类似 SQL 的 JOIN，按共同列合并两个表
                if df_basic is not None and not df_basic.empty:
                    df = pd.merge(
                        df_daily, df_basic, on=["ts_code", "trade_date"], how="left"
                    )
                else:
                    df = df_daily
                    df["total_mv"] = None
                    df["turnover_rate"] = None

                # 批量写入数据库
                # 【学习要点】用原生 SQL 的 INSERT OR REPLACE 实现批量 upsert
                # 比逐条 ORM 操作快很多倍
                records = []
                for _, row in df.iterrows():
                    records.append(
                        {
                            "ts_code": row["ts_code"],
                            "trade_date": row["trade_date"],
                            "open": row.get("open"),
                            "high": row.get("high"),
                            "low": row.get("low"),
                            "close": row.get("close"),
                            "vol": row.get("vol"),
                            "amount": row.get("amount"),
                            "pct_chg": row.get("pct_chg"),
                            "total_mv": row.get("total_mv"),
                            "turnover_rate": row.get("turnover_rate"),
                        }
                    )

                if records:
                    db.execute(text("DELETE FROM daily_quote WHERE trade_date = :d"), {"d": date})
                    db.execute(DailyQuote.__table__.insert(), records)
                    db.commit()

                if (i + 1) % 10 == 0 or i == len(trade_dates) - 1:
                    print(f"  进度：{i + 1}/{len(trade_dates)} ({date})")

            except Exception as e:
                print(f"  警告：{date} 数据拉取失败 - {e}")
                db.rollback()
                time.sleep(1)  # 出错后多等一会儿
                continue
    finally:
        db.close()


def sync_financial_data():
    """
    同步财务数据

    拉取所有股票的关键财务指标，用于"扣非归母净利润连续三年增长"条件。

    【学习要点】
    财务数据的特殊性：
    - 不像行情数据每天更新，财务数据按季度报告期更新
    - 年报(12月31日)、中报(6月30日)、一季报(3月31日)、三季报(9月30日)
    - 我们主要关注年报数据（end_date 以 1231 结尾）
    - Tushare 的 fina_indicator 接口按股票代码拉取
    """
    print("\n=== 同步财务数据 ===")
    pro = get_tushare_api()

    # 先获取所有股票代码
    db = SessionLocal()
    try:
        stocks = db.query(StockBasic.ts_code).all()
        ts_codes = [s[0] for s in stocks]
    finally:
        db.close()

    print(f"共 {len(ts_codes)} 只股票需要同步财务数据")

    db = SessionLocal()
    total_records = 0
    try:
        for i, code in enumerate(ts_codes):
            try:
                # 拉取该股票的财务指标
                df = pro.fina_indicator(
                    ts_code=code,
                    fields="ts_code,ann_date,end_date,profit_dedt,revenue",
                )
                time.sleep(0.3)

                if df is None or df.empty:
                    continue

                # 只保留年报数据（end_date 以 1231 结尾）
                df = df[df["end_date"].str.endswith("1231")]

                if df.empty:
                    continue

                # 去重：同一报告期保留最新公告
                df = df.sort_values("ann_date", ascending=False)
                df = df.drop_duplicates(subset=["ts_code", "end_date"], keep="first")

                for _, row in df.iterrows():
                    ann_date = row.get("ann_date") or "00000000"
                    existing = db.get(
                        StockFinancial, (row["ts_code"], ann_date, row["end_date"])
                    )
                    if not existing:
                        record = StockFinancial(
                            ts_code=row["ts_code"],
                            ann_date=ann_date,
                            end_date=row["end_date"],
                            profit_dedt=row.get("profit_dedt"),
                            revenue=row.get("revenue"),
                        )
                        db.add(record)
                        total_records += 1

                # 每 100 只股票提交一次
                if (i + 1) % 100 == 0:
                    db.commit()
                    print(f"  进度：{i + 1}/{len(ts_codes)}，累计 {total_records} 条")

            except Exception as e:
                print(f"  警告：{code} 财务数据拉取失败 - {e}")
                db.rollback()
                time.sleep(1)
                continue

        db.commit()
        print(f"财务数据同步完成，共 {total_records} 条")
    finally:
        db.close()


def run_full_sync():
    """
    运行完整的数据同步流程

    这是 MVP 的一键数据初始化入口。
    按顺序执行：建表 → 股票列表 → 行情数据 → 财务数据
    """
    print("=" * 60)
    print("开始全量数据同步")
    print("=" * 60)

    # 第一步：建表
    init_database()

    # 第二步：同步股票列表
    sync_stock_basic()

    # 第三步：同步近 30 天行情数据
    # MVP 只需验证链路跑通，30 天够算 MA20
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=45)).strftime("%Y%m%d")
    sync_daily_quotes(start_date, end_date)

    # 第四步：跳过财务数据（MVP 不需要，正式版再加）
    print("\n=== 跳过财务数据（MVP 阶段） ===")

    print("\n" + "=" * 60)
    print("全量数据同步完成！")
    print("=" * 60)


# 当直接运行这个文件时执行同步
# 【学习要点】
# if __name__ == "__main__" 是 Python 的常用模式：
# - 直接运行此文件（python data_sync.py）→ 执行下面的代码
# - 被其他文件 import → 不执行，只提供函数供调用
if __name__ == "__main__":
    run_full_sync()
