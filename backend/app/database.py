"""
数据库连接模块

【学习要点】
- SQLAlchemy 是 Python 最流行的 ORM（对象关系映射）框架
- ORM 的作用：让你用 Python 类和对象操作数据库，而不是写原始 SQL
- Engine 是数据库连接的核心，Session 是每次操作数据库的"会话"
- DeclarativeBase 是所有数据模型的基类，相当于"所有表的祖先"
"""

from sqlalchemy import event, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import DATABASE_URL

# 创建数据库引擎
# echo=False 表示不在终端打印每条 SQL（调试时可改为 True）
engine = create_engine(DATABASE_URL, echo=False)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """每次建立连接时开启外键约束（SQLite 默认关闭）"""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# 创建 Session 工厂
# 每次需要操作数据库时，调用 SessionLocal() 创建一个会话
SessionLocal = sessionmaker(bind=engine)


# 所有数据模型的基类
class Base(DeclarativeBase):
    pass


def get_db():
    """
    获取数据库会话的生成器函数

    【学习要点】
    这是 FastAPI 的"依赖注入"模式：
    - API 路由函数声明"我需要一个数据库会话"
    - FastAPI 自动调用这个函数来提供
    - yield 之前的代码在请求开始时执行（创建会话）
    - yield 之后的代码在请求结束时执行（关闭会话）
    - 这样确保每个请求都有独立的数据库会话，用完自动关闭
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
