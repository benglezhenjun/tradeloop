"""项目级常量定义。"""

# 应用版本（单一来源）：FastAPI metadata、/api/health、/api/ready 共用。
APP_VERSION = "8.0.0"

# daily_quote.amount 存储单位为千元，除以该值后可得到亿元。
AMOUNT_UNIT_TO_YI = 100_000

# daily_quote.total_mv 存储单位为万元，除以该值后可得到亿元。
MV_UNIT_TO_YI = 10_000
