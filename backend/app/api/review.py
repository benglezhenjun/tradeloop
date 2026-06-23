from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import raise_service_error
from app.services import pattern as pattern_service
from app.services import review as review_service
from app.services.agents import review as review_agent

router = APIRouter(prefix="/review", tags=["review"])


class NotesUpdate(BaseModel):
    notes: str


class PatternStatusUpdate(BaseModel):
    status: Literal["active", "resolved", "dismissed"]


@router.post("/generate/{ts_code}", status_code=201)
def generate_review(ts_code: str, db: Session = Depends(get_db)):
    agent_result = review_agent.run_review_agent(db, ts_code)
    if "error" in agent_result:
        raise_service_error(agent_result)

    result = review_service.create_review(db, ts_code, agent_result)
    if "error" in result:
        raise_service_error(result)
    return result


@router.get("")
def list_reviews(ts_code: str | None = Query(None), db: Session = Depends(get_db)):
    result = review_service.list_reviews(db, ts_code=ts_code)
    if "error" in result:
        raise_service_error(result)
    return result


@router.get("/stats")
def get_review_stats(db: Session = Depends(get_db)):
    result = review_service.get_review_stats(db)
    if "error" in result:
        raise_service_error(result)
    return result


@router.get("/patterns")
def list_patterns(status: str | None = Query(None), db: Session = Depends(get_db)):
    result = pattern_service.list_patterns(db, status=status)
    if "error" in result:
        raise_service_error(result)
    return result


@router.post("/patterns/refresh")
def refresh_patterns(db: Session = Depends(get_db)):
    agent_result = review_agent.run_pattern_agent(db)
    if "error" in agent_result:
        raise_service_error(agent_result)

    result = pattern_service.save_patterns(db, agent_result["patterns"])
    if "error" in result:
        raise_service_error(result)
    return result


@router.patch("/patterns/{pattern_id}/status")
def update_pattern_status(pattern_id: int, body: PatternStatusUpdate, db: Session = Depends(get_db)):
    result = pattern_service.update_pattern_status(db, pattern_id, body.status)
    if "error" in result:
        raise_service_error(result)
    return result


@router.get("/{review_id}")
def get_review_detail(review_id: int, db: Session = Depends(get_db)):
    result = review_service.get_review_detail(db, review_id)
    if result is None:
        raise HTTPException(status_code=404, detail="复盘记录不存在")
    return result


@router.put("/{review_id}/notes")
def update_review_notes(review_id: int, body: NotesUpdate, db: Session = Depends(get_db)):
    result = review_service.update_review_notes(db, review_id, body.notes)
    if "error" in result:
        raise_service_error(result)
    return result


@router.delete("/{review_id}")
def delete_review(review_id: int, db: Session = Depends(get_db)):
    result = review_service.delete_review(db, review_id)
    if "error" in result:
        raise_service_error(result)
    return result
