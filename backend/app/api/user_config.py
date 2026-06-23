"""
用户配置 API (V5)

  GET  /api/config/{key}   — 获取配置
  PUT  /api/config/{key}   — 设置配置
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import user_config

router = APIRouter()


class ConfigUpdate(BaseModel):
    value: str


@router.get("/config/{key}")
def get_config(key: str, db: Session = Depends(get_db)):
    """获取指定配置项的值"""
    val = user_config.get_config(db, key)
    if val is None:
        raise HTTPException(status_code=404, detail=f"配置项 {key} 不存在")
    return {"key": key, "value": val}


@router.put("/config/{key}")
def set_config(key: str, body: ConfigUpdate, db: Session = Depends(get_db)):
    """设置指定配置项的值"""
    result = user_config.set_config(db, key, body.value)
    return result
