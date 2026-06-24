"""API 密钥管理：前端填写 Tushare / LLM 凭证，存本地 DB，保存即生效，支持联网校验。

- GET  /api/credentials        — 打码状态（已配置?、头尾4位、LLM provider/model/base_url）
- PUT  /api/credentials        — 保存（只写非空字段；空字段=不改，避免清掉已存 key）
- POST /api/credentials/check  — 实时联网校验（Tushare 拉交易日历 / LLM 列模型，均不消耗对话额度）
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import credentials
from app.database import get_db

router = APIRouter(prefix="/api/credentials", tags=["凭证"])


class CredentialUpdate(BaseModel):
    tushare_token: str | None = None
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_model: str | None = None


@router.get("")
def get_credentials():
    """返回打码后的凭证状态（绝不返回完整 key）。"""
    return credentials.status()


@router.put("")
def update_credentials(body: CredentialUpdate, db: Session = Depends(get_db)):
    """保存凭证到本地 DB，并即时生效（无需重启）。"""
    credentials.save(db, body.model_dump())
    return credentials.status()


def _check_tushare() -> dict:
    token = credentials.tushare_token()
    if not token:
        return {"ok": False, "reason": "未配置"}
    try:
        import tushare as ts

        pro = ts.pro_api(token)
        # 交易日历是最轻量的接口之一，足以验证 token 是否有效
        pro.trade_cal(exchange="SSE", start_date="20260101", end_date="20260102")
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001 — 校验需吞掉一切异常并回报原因
        return {"ok": False, "reason": str(exc)[:160]}


def _check_llm() -> dict:
    from app.services import llm

    if not llm.is_configured():
        return {"ok": False, "reason": "未配置"}
    try:
        # 列模型不消耗对话 token，足以验证 key/base_url 是否可用
        client = llm._get_client()
        client.models.list()
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": str(exc)[:160]}


@router.post("/check")
def check_credentials():
    """实时联网校验两类凭证，返回各自 ok/reason。"""
    return {"tushare": _check_tushare(), "llm": _check_llm()}
