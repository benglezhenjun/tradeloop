"""共享错误构造与 API 层异常转换。"""

from __future__ import annotations

from typing import Any, NoReturn

from fastapi import HTTPException


def build_error(message: str, error_type: str = "validation") -> dict[str, Any]:
    return {"error": message, "error_type": error_type}


def raise_service_error(result: dict[str, Any]) -> NoReturn:
    error_type = result.get("error_type", "validation")
    message = result["error"]
    if error_type == "not_found":
        raise HTTPException(status_code=404, detail=message)
    if error_type == "upstream":
        raise HTTPException(status_code=502, detail=message)
    raise HTTPException(status_code=400, detail=message)
