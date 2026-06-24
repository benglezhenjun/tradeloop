"""
用户配置 API (V5)

  GET  /api/config/{key}   — 获取配置
  PUT  /api/config/{key}   — 设置配置
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.credentials import RESERVED_KEYS
from app.database import get_db
from app.services import user_config

router = APIRouter()


class ConfigUpdate(BaseModel):
    value: str


def _guard_reserved(key: str) -> None:
    """凭证键禁止经通用配置接口读写，避免绕过 /api/credentials 的打码读出明文 key。"""
    if key in RESERVED_KEYS:
        raise HTTPException(status_code=403, detail="该配置项受保护，请在「设置 → API 密钥」中管理")


@router.get("/config/{key}")
def get_config(key: str, db: Session = Depends(get_db)):
    """获取指定配置项的值"""
    _guard_reserved(key)
    val = user_config.get_config(db, key)
    if val is None:
        raise HTTPException(status_code=404, detail=f"配置项 {key} 不存在")
    return {"key": key, "value": val}


@router.put("/config/{key}")
def set_config(key: str, body: ConfigUpdate, db: Session = Depends(get_db)):
    """设置指定配置项的值"""
    _guard_reserved(key)
    result = user_config.set_config(db, key, body.value)
    return result
