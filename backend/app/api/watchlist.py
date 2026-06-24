"""自选股管理 API"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.envelope import list_envelope
from app.database import get_db
from app.errors import raise_service_error
from app.services import watchlist as watchlist_svc

router = APIRouter(prefix="/api/watchlist", tags=["自选股"])


# ---- 请求体模型 ----

class GroupCreate(BaseModel):
    name: str
    description: str = ""


class GroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    sort_order: int | None = None


class StockAdd(BaseModel):
    ts_code: str
    note: str = ""


class BatchAdd(BaseModel):
    group_id: int
    ts_codes: list[str]


# ---- 分组路由 ----

@router.get("/groups")
def list_groups(db: Session = Depends(get_db)):
    """获取所有自选股分组（统一列表信封 {items,total}）"""
    return list_envelope(watchlist_svc.list_groups(db))


@router.post("/groups")
def create_group(body: GroupCreate, db: Session = Depends(get_db)):
    """创建新分组"""
    return watchlist_svc.create_group(db, body.name, body.description)


@router.patch("/groups/{group_id}")
def update_group(group_id: int, body: GroupUpdate, db: Session = Depends(get_db)):
    """修改分组信息"""
    result = watchlist_svc.update_group(db, group_id, name=body.name, description=body.description, sort_order=body.sort_order)
    if not result:
        raise HTTPException(status_code=404, detail=f"分组 {group_id} 不存在")
    return result


@router.delete("/groups/{group_id}")
def delete_group(group_id: int, db: Session = Depends(get_db)):
    """删除分组（自动清理内部股票）"""
    if not watchlist_svc.delete_group(db, group_id):
        raise HTTPException(status_code=404, detail=f"分组 {group_id} 不存在")
    return {"message": "已删除"}


# ---- 分组内股票路由 ----

@router.get("/groups/{group_id}/stocks")
def group_stocks(group_id: int, db: Session = Depends(get_db)):
    """获取分组内的股票列表（含最新行情数据）"""
    stocks = watchlist_svc.get_group_stocks(db, group_id)
    if stocks is None:
        raise HTTPException(status_code=404, detail=f"分组 {group_id} 不存在")
    return list_envelope(stocks)


@router.post("/groups/{group_id}/stocks")
def add_stock(group_id: int, body: StockAdd, db: Session = Depends(get_db)):
    """往分组里添加一只股票"""
    result = watchlist_svc.add_stock(db, group_id, body.ts_code, body.note)
    if "error" in result:
        raise_service_error(result)
    return result


@router.delete("/groups/{group_id}/stocks/{ts_code}")
def remove_stock(group_id: int, ts_code: str, db: Session = Depends(get_db)):
    """从分组里移除一只股票"""
    if not watchlist_svc.remove_stock(db, group_id, ts_code):
        raise HTTPException(status_code=404, detail=f"分组 {group_id} 中未找到 {ts_code}")
    return {"message": "已移除"}


# ---- 汇总路由 ----

@router.get("/stocks")
def all_stocks(db: Session = Depends(get_db)):
    """获取所有自选股（去重，含最新行情；统一列表信封 {items,total}）"""
    return list_envelope(watchlist_svc.get_all_stocks(db))


@router.post("/stocks/batch")
def batch_add(body: BatchAdd, db: Session = Depends(get_db)):
    """批量添加股票到指定分组（从筛选结果一键添加）"""
    result = watchlist_svc.batch_add_stocks(db, body.group_id, body.ts_codes)
    if "error" in result:
        raise_service_error(result)
    return result
