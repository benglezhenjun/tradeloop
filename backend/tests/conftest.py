"""
全局 pytest fixture（公共数据库脚手架）。

【为什么集中到 conftest】
此前每个测试文件都各自定义了一遍 `engine` / `db` fixture（17 份近乎重复），
维护成本高且容易漂移。这里统一抽出权威实现：

- 用内存 SQLite + StaticPool，使同一个内存库能被多个连接/线程共享——
  这对 FastAPI TestClient（请求在另一线程跑）是必需的，对纯单连接的
  service 测试也完全兼容，所以一份实现覆盖两类场景。
- 每次连接开启外键约束，与生产 `app.database` 行为一致。

测试文件无需再自带 `engine` / `db`，直接把它们当参数注入即可；如需特殊
引擎仍可在本地覆盖同名 fixture（pytest 就近优先）。
"""

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def engine():
    """内存 SQLite 引擎；StaticPool 让所有连接共享同一个内存库。"""
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

    import app.models  # noqa: F401 — 触发所有表注册到 Base.metadata
    from app.database import Base

    Base.metadata.create_all(bind=eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine):
    """与 `engine` 绑定的数据库会话。"""
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
