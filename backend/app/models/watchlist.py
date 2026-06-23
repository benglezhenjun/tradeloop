"""
自选股相关数据表

WatchlistGroup   ← 自选股分组（相当于"文件夹"，用户自己创建���
WatchlistStock   ← 分组里的股票（哪只股票放在哪个分组）
"""

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func

from app.database import Base


class WatchlistGroup(Base):
    """
    自选股分组表

    用户可以创建多个分组来管理自选股，比如"重点关注"、"短线候选"等。
    """

    __tablename__ = "watchlist_group"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, comment="分组名称")
    description = Column(String(200), comment="分组说明")
    sort_order = Column(Integer, default=0, comment="排序，数字越小越靠前")
    created_at = Column(DateTime, server_default=func.now())


class WatchlistStock(Base):
    """
    自选股明细表

    记录某只股票被放入了哪个分组，以及用户的备注。
    同一个分组内不能重复添加同一只股票（UNIQUE 约束）。
    删除分组时，里面的股票记录会自动清理（CASCADE）。
    """

    __tablename__ = "watchlist_stock"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(
        Integer,
        ForeignKey("watchlist_group.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属分组",
    )
    ts_code = Column(String(20), nullable=False, comment="股票代码，如 000001.SZ")
    note = Column(String(200), comment="备注（为什么关注这只股票）")
    added_at = Column(DateTime, server_default=func.now(), comment="加入时间")

    __table_args__ = (
        UniqueConstraint("group_id", "ts_code", name="uq_group_stock"),
        Index("ix_ws_group", "group_id"),
        Index("ix_ws_code", "ts_code"),
    )
