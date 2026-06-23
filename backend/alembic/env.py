"""
Alembic 迁移环境配置

【学习要点 - Alembic 是什么？】
Alembic 是数据库迁移工具。当你修改了数据模型（比如新增一张表），
Alembic 可以自动生成"迁移脚本"，并在数据库上执行这些改动。

好处：数据库结构变更有历史记录，新机器部署时可以一键同步结构，
不需要手动执行 SQL。
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# 把 backend/ 加入 Python 路径，这样才能导入 app.*
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import DATABASE_URL
from app.database import Base

# 导入所有模型，让 Alembic 能感知到所有表
import app.models  # noqa: F401

alembic_config = context.config
alembic_config.set_main_option("sqlalchemy.url", DATABASE_URL)

if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

# 让 Alembic 知道我们所有表的结构，用于自动生成迁移脚本
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = alembic_config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        alembic_config.get_section(alembic_config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
