"""
交易计划 API (V5)

  POST   /api/plan                     — 保存计划
  GET    /api/plan                     — 计划列表
  GET    /api/plan/{plan_id}           — 计划详情
  PUT    /api/plan/{plan_id}           — 编辑计划
  PATCH  /api/plan/{plan_id}/status    — 变更状态
  DELETE /api/plan/{plan_id}           — 删除计划
  POST   /api/plan/generate/{ts_code}  — LLM 生成三套方案
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.envelope import list_envelope
from app.database import get_db
from app.errors import raise_service_error
from app.services import plan as plan_service
from app.services import user_config
from app.services.agents import run_plan_agent

router = APIRouter()


class PlanCreate(BaseModel):
    ts_code: str
    stock_name: str
    direction: Literal["buy", "sell"]
    target_price: float
    stop_loss_price: float
    take_profit: list
    position_ratio: float = Field(ge=0, le=0.4)
    reasoning: str = ""
    risk_comment: str | None = None
    tier_label: str | None = None
    source: Literal["llm_generated", "manual"] = "manual"
    expiry_date: str | None = None
    alternatives: list | None = None


class PlanUpdate(BaseModel):
    direction: Literal["buy", "sell"] | None = None
    target_price: float | None = None
    stop_loss_price: float | None = None
    take_profit: list | None = None
    position_ratio: float | None = None
    reasoning: str | None = None
    risk_comment: str | None = None
    tier_label: str | None = None
    expiry_date: str | None = None


class StatusUpdate(BaseModel):
    status: Literal["executed", "abandoned"]


@router.post("/plan", status_code=201)
def create_plan(body: PlanCreate, db: Session = Depends(get_db)):
    """保存交易计划（用户选定/编辑后提交，或手动创建）"""
    result = plan_service.create_plan(db, body.model_dump())
    if "error" in result:
        raise_service_error(result)
    return result


@router.get("/plan")
def list_plans(
    status: str | None = Query(None),
    ts_code: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """获取计划列表，支持按状态和股票筛选（统一列表信封 {items,total}）"""
    return list_envelope(plan_service.get_plans(db, status=status, ts_code=ts_code))


@router.get("/plan/{plan_id}")
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    """获取计划详情（含备选方案）"""
    result = plan_service.get_plan_detail(db, plan_id)
    if result is None:
        raise HTTPException(status_code=404, detail="计划不存在")
    return result


@router.put("/plan/{plan_id}")
def update_plan(plan_id: int, body: PlanUpdate, db: Session = Depends(get_db)):
    """编辑计划（仅 pending 状态）"""
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")
    result = plan_service.update_plan(db, plan_id, updates)
    if "error" in result:
        raise_service_error(result)
    return result


@router.patch("/plan/{plan_id}/status")
def update_plan_status(plan_id: int, body: StatusUpdate, db: Session = Depends(get_db)):
    """变更计划状态（pending → executed 或 pending → abandoned）"""
    result = plan_service.update_plan_status(db, plan_id, body.status)
    if "error" in result:
        raise_service_error(result)
    return result


@router.delete("/plan/{plan_id}")
def delete_plan(plan_id: int, db: Session = Depends(get_db)):
    """删除计划"""
    success = plan_service.delete_plan(db, plan_id)
    if not success:
        raise HTTPException(status_code=404, detail="计划不存在")
    return {"message": "已删除"}


@router.post("/plan/generate/{ts_code}")
def generate_plans(ts_code: str, db: Session = Depends(get_db)):
    """LLM 生成三套交易方案（不落库，返回给前端供用户选择）"""
    capital_str = user_config.get_config(db, "total_capital")
    try:
        total_capital = float(capital_str) if capital_str else 0.0
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="总资金格式错误，请在设置页重新设置")
    if total_capital <= 0:
        raise HTTPException(status_code=400, detail="请先在设置页设置总资金")
    result = run_plan_agent(db, ts_code, total_capital)
    if result.get("status") == "manual_fallback":
        return result
    if "error" in result:
        raise_service_error(result)
    return result
