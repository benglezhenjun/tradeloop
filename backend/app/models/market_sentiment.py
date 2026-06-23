"""市场情绪日级快照表。"""

from sqlalchemy import Column, Float, Index, Integer, String, Text

from app.database import Base


class MarketSentimentDaily(Base):
    __tablename__ = "market_sentiment_daily"

    trade_date = Column(String(8), primary_key=True, comment="交易日期 YYYYMMDD")
    max_limit_height = Column(Integer, nullable=False, default=0)
    max_limit_height_count = Column(Integer, nullable=False, default=0)
    max_limit_height_codes_json = Column(Text, nullable=False, default="[]")
    limit_up_count = Column(Integer, nullable=False, default=0)
    limit_broken_count = Column(Integer, nullable=False, default=0)
    broken_rate = Column(Float, nullable=False, default=0.0)
    yday_limit_premium_avg = Column(Float, nullable=False, default=0.0)
    yday_limit_premium_median = Column(Float, nullable=False, default=0.0)
    yday_limit_red_rate = Column(Float, nullable=False, default=0.0)
    yday_limit_sample_count = Column(Integer, nullable=False, default=0)
    high_board_threshold = Column(Integer, nullable=False, default=3)
    high_board_total = Column(Integer, nullable=False, default=0)
    high_board_advanced = Column(Integer, nullable=False, default=0)
    high_board_promotion_rate = Column(Float, nullable=False, default=0.0)
    main_theme_code = Column(String(50), nullable=True)
    main_theme_name = Column(String(100), nullable=True)
    main_theme_score = Column(Float, nullable=True)
    main_theme_streak_days = Column(Integer, nullable=False, default=0)
    notes_json = Column(Text, nullable=False, default="{}")

    __table_args__ = (
        Index("ix_market_sentiment_trade_date", "trade_date"),
    )
