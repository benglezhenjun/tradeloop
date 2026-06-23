"""策略管理 API"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import strategy as strategy_svc
from app.services.conditions import registry

router = APIRouter(prefix="/api/strategies", tags=["策略"])


# ---- 请求体模型 ----

class StrategyCreate(BaseModel):
    name: str
    description: str = ""


class StrategyUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_enabled: bool | None = None


class ConditionItem(BaseModel):
    condition_code: str
    params: dict = {}
    is_enabled: bool = True
    sort_order: int = 0


class ConditionsUpdate(BaseModel):
    conditions: list[ConditionItem]


# ---- 路由 ----

@router.get("")
def list_strategies(db: Session = Depends(get_db)):
    """获取所有策略列表"""
    return {"strategies": strategy_svc.list_strategies(db)}


@router.get("/conditions/all")
def list_all_conditions():
    """获取系统中所有可用条件（供策略编辑器展示）"""
    return {"conditions": registry.all()}


@router.get("/{strategy_id}")
def get_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """获取单个策略的详情（含条件列表）"""
    detail = strategy_svc.get_strategy_detail(db, strategy_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"策略 {strategy_id} 不存在")
    return detail


@router.post("")
def create_strategy(body: StrategyCreate, db: Session = Depends(get_db)):
    """创建新策略"""
    return strategy_svc.create_strategy(db, body.name, body.description)


@router.patch("/{strategy_id}")
def update_strategy(strategy_id: int, body: StrategyUpdate, db: Session = Depends(get_db)):
    """更新策略基本信息"""
    result = strategy_svc.update_strategy(
        db, strategy_id,
        name=body.name,
        description=body.description,
        is_enabled=body.is_enabled,
    )
    if not result:
        raise HTTPException(status_code=404, detail=f"策略 {strategy_id} 不存在")
    return result


@router.delete("/{strategy_id}")
def delete_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """删除策略"""
    if not strategy_svc.delete_strategy(db, strategy_id):
        raise HTTPException(status_code=404, detail=f"策略 {strategy_id} 不存在")
    return {"message": "已删除"}


@router.put("/{strategy_id}/conditions")
def update_conditions(strategy_id: int, body: ConditionsUpdate, db: Session = Depends(get_db)):
    """替换策略的条件列表"""
    ok = strategy_svc.update_strategy_conditions(
        db, strategy_id,
        [c.model_dump() for c in body.conditions],
    )
    if not ok:
        raise HTTPException(status_code=404, detail=f"策略 {strategy_id} 不存在")
    return {"message": "条件已更新"}
