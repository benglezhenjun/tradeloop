"""
策略管理服务

提供策略的 CRUD 操作，以及内置策略的初始化。
"""

import json

from sqlalchemy.orm import Session

from app.models.strategy import Condition, Strategy, StrategyCondition
from app.services.conditions import registry


# ====================================================
# 内置策略定义（系统初始化时自动创建）
# ====================================================

# 通用示例策略：仅用于演示插件式选股引擎（多条件 AND 组合），均为教科书式简单组合，
# 不代表任何具体投资建议。用户可在「策略管理」页自由增删条件、组合自己的策略。
BUILTIN_STRATEGIES = [
    {
        "name": "示例策略：放量大盘股",
        "description": "演示用：成交额与市值双门槛，过滤出流动性好的大盘股。",
        "conditions": [
            {"code": "amount_gt",     "params": {"threshold": 2},   "sort": 1},  # 成交额 ≥ 2 亿元
            {"code": "market_cap_gt", "params": {"threshold": 100}, "sort": 2},  # 总市值 ≥ 100 亿元
        ],
    },
    {
        "name": "示例策略：站上 20 日线",
        "description": "演示用：收盘价站上 20 日均线且偏离有限，叠加成交额门槛。",
        "conditions": [
            {"code": "ma_proximity", "params": {"ma_period": 20, "deviation_max": 0.08}, "sort": 1},
            {"code": "amount_gt",    "params": {"threshold": 1}, "sort": 2},  # 成交额 ≥ 1 亿元
        ],
    },
]


def init_conditions(db: Session):
    """将注册器中的所有条件同步到数据库 condition 表"""
    for schema in registry.all():
        existing = db.get(Condition, schema["code"])
        if not existing:
            db.add(Condition(
                code=schema["code"],
                name=schema["name"],
                category=schema["category"],
                description=schema["description"],
                param_schema=json.dumps(schema["params"], ensure_ascii=False),
            ))
    db.commit()


def init_builtin_strategies(db: Session):
    """初始化内置策略（已存在则跳过）"""
    init_conditions(db)

    for spec in BUILTIN_STRATEGIES:
        existing = db.query(Strategy).filter(Strategy.name == spec["name"]).first()
        if existing:
            continue

        strategy = Strategy(name=spec["name"], description=spec["description"])
        db.add(strategy)
        db.flush()

        for cond in spec["conditions"]:
            db.add(StrategyCondition(
                strategy_id=strategy.id,
                condition_code=cond["code"],
                params=json.dumps(cond["params"], ensure_ascii=False),
                sort_order=cond["sort"],
            ))

    db.commit()


# ====================================================
# CRUD 操作
# ====================================================

def list_strategies(db: Session) -> list[dict]:
    strategies = db.query(Strategy).order_by(Strategy.id).all()
    result = []
    for s in strategies:
        conditions = (
            db.query(StrategyCondition)
            .filter(StrategyCondition.strategy_id == s.id)
            .order_by(StrategyCondition.sort_order)
            .all()
        )
        result.append({
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "is_enabled": s.is_enabled,
            "condition_count": len(conditions),
            "created_at": s.created_at.isoformat() if s.created_at else None,
        })
    return result


def get_strategy_detail(db: Session, strategy_id: int) -> dict | None:
    strategy = db.get(Strategy, strategy_id)
    if not strategy:
        return None

    conditions = (
        db.query(StrategyCondition)
        .filter(StrategyCondition.strategy_id == strategy_id)
        .order_by(StrategyCondition.sort_order)
        .all()
    )

    cond_list = []
    for sc in conditions:
        cond_def = db.get(Condition, sc.condition_code)
        cond_list.append({
            "id": sc.id,
            "condition_code": sc.condition_code,
            "condition_name": cond_def.name if cond_def else sc.condition_code,
            "category": cond_def.category if cond_def else "",
            "params": sc.get_params(),
            "param_schema": json.loads(cond_def.param_schema) if cond_def else {},
            "is_enabled": sc.is_enabled,
            "sort_order": sc.sort_order,
        })

    return {
        "id": strategy.id,
        "name": strategy.name,
        "description": strategy.description,
        "is_enabled": strategy.is_enabled,
        "conditions": cond_list,
    }


def create_strategy(db: Session, name: str, description: str = "") -> dict:
    strategy = Strategy(name=name, description=description)
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    return {"id": strategy.id, "name": strategy.name}


def update_strategy(db: Session, strategy_id: int, name: str | None = None,
                    description: str | None = None, is_enabled: bool | None = None) -> dict | None:
    strategy = db.get(Strategy, strategy_id)
    if not strategy:
        return None
    if name is not None:
        strategy.name = name
    if description is not None:
        strategy.description = description
    if is_enabled is not None:
        strategy.is_enabled = is_enabled
    db.commit()
    return {"id": strategy.id, "name": strategy.name}


def delete_strategy(db: Session, strategy_id: int) -> bool:
    strategy = db.get(Strategy, strategy_id)
    if not strategy:
        return False
    db.delete(strategy)
    db.commit()
    return True


def update_strategy_conditions(db: Session, strategy_id: int, conditions: list[dict]) -> bool:
    """
    替换策略的条件列表

    conditions 格式（threshold 单位见各条件定义，amount_gt/market_cap_gt 为亿元）：
    [{"condition_code": "amount_gt", "params": {"threshold": 2}, "is_enabled": true, "sort_order": 1}]
    """
    strategy = db.get(Strategy, strategy_id)
    if not strategy:
        return False

    # 删除旧条件
    db.query(StrategyCondition).filter(StrategyCondition.strategy_id == strategy_id).delete()

    # 插入新条件
    for cond in conditions:
        db.add(StrategyCondition(
            strategy_id=strategy_id,
            condition_code=cond["condition_code"],
            params=json.dumps(cond.get("params", {}), ensure_ascii=False),
            is_enabled=cond.get("is_enabled", True),
            sort_order=cond.get("sort_order", 0),
        ))

    db.commit()
    return True
