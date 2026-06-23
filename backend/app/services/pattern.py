from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.errors import build_error
from app.models.review import BehaviorPattern
from app.services.plan_contract import now_iso
from app.services.review_contract import format_pattern

VALID_PATTERN_STATUSES = ("active", "resolved", "dismissed")


def list_patterns(db: Session, status: str | None = None) -> dict[str, list[dict[str, Any]]] | dict[str, Any]:
    if status is not None and status not in VALID_PATTERN_STATUSES:
        return build_error(f"status 必须是 {VALID_PATTERN_STATUSES}")

    query = db.query(BehaviorPattern)
    if status:
        query = query.filter(BehaviorPattern.status == status)
    query = query.order_by(BehaviorPattern.updated_at.desc(), BehaviorPattern.id.desc())
    return {"patterns": [format_pattern(pattern) for pattern in query.all()]}


def save_patterns(db: Session, patterns_data: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    db.query(BehaviorPattern).filter(BehaviorPattern.status == "active").delete()

    now = now_iso()
    for pattern_data in patterns_data:
        pattern = BehaviorPattern(
            pattern_type=pattern_data["pattern_type"],
            title=pattern_data["title"],
            description=pattern_data["description"],
            dimension=pattern_data.get("dimension"),
            evidence_ids=json.dumps(pattern_data.get("evidence_ids", []), ensure_ascii=False),
            status=pattern_data.get("status", "active"),
            created_at=now,
            updated_at=now,
        )
        db.add(pattern)

    db.commit()
    return list_patterns(db)


def update_pattern_status(db: Session, pattern_id: int, status: str) -> dict[str, Any]:
    if status not in VALID_PATTERN_STATUSES:
        return build_error(f"status 必须是 {VALID_PATTERN_STATUSES}")

    pattern = db.get(BehaviorPattern, pattern_id)
    if pattern is None:
        return build_error("行为模式不存在", "not_found")

    pattern.status = status
    pattern.updated_at = now_iso()
    db.commit()
    db.refresh(pattern)
    return format_pattern(pattern)
