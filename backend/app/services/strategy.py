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

BUILTIN_STRATEGIES = [
    {
        "name": "策略1：热点追踪",
        "description": "筛选当前最热门、流动性好、基本面过关的股票。适合趋势行情中寻找强势股。",
        "conditions": [
            {"code": "amount_gt",     "params": {"threshold": 2_000_000_000}, "sort": 1},
            {"code": "amount_rank",   "params": {"top_n": 100},               "sort": 2},
            {"code": "market_cap_gt", "params": {"threshold": 10_000_000_000}, "sort": 3},
            {"code": "ma_proximity",  "params": {"ma_period": 20, "deviation_max": 0.06}, "sort": 4},
            {"code": "profit_growth", "params": {"years": 3},                 "sort": 5},
        ],
    },
    {
        "name": "策略2：年线回踩",
        "description": "寻找曾经大涨、年线趋势向上、当前价格回踩年线附近的股票。适合寻找二次启动机会。",
        "conditions": [
            {"code": "ma_slope",         "params": {"ma_period": 240, "slope_window": 20, "slope_max": 0.002}, "sort": 1},
            {"code": "price_rise_range", "params": {"days": 240, "min_rise": 0.5},            "sort": 2},
            {"code": "ma_proximity",     "params": {"ma_period": 240, "deviation_max": 0.06}, "sort": 3},
            {"code": "multi_ma_alignment", "params": {"mode": "loose"},                       "sort": 4},
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

    conditions 格式：
    [{"condition_code": "amount_gt", "params": {"threshold": 2e9}, "is_enabled": true, "sort_order": 1}]
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
