from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from tests.test_v7_review import (
    create_pattern_row,
    create_review_row,
    prepare_trade_cycle,
    sample_llm_result,
)


@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite://",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(eng, "connect")
    def _set_pragma(dbapi_connection, _):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    import app.models  # noqa: F401
    from app.database import Base

    Base.metadata.create_all(bind=eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def client(db):
    from app.api import review as review_api
    from app.database import get_db

    app = FastAPI()
    app.include_router(review_api.router, prefix="/api")

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


class TestReviewApi:
    @patch("app.services.agents.review.run_review_agent")
    def test_generate_review_returns_created_review(self, mock_run_review_agent, client, db):
        prepare_trade_cycle(db)
        mock_run_review_agent.return_value = {
            "status": "ok",
            **sample_llm_result(),
        }

        response = client.post("/api/review/generate/600000.SH")

        assert response.status_code == 201
        assert response.json()["ts_code"] == "600000.SH"
        assert response.json()["overall_score"] == 7.1

    def test_list_reviews(self, client, db):
        create_review_row(db)

        response = client.get("/api/review")

        assert response.status_code == 200
        assert len(response.json()["reviews"]) == 1

    def test_get_review_detail(self, client, db):
        review = create_review_row(db)

        response = client.get(f"/api/review/{review.id}")

        assert response.status_code == 200
        assert response.json()["id"] == review.id

    def test_update_review_notes(self, client, db):
        review = create_review_row(db)

        response = client.put(f"/api/review/{review.id}/notes", json={"notes": "补充反思"})

        assert response.status_code == 200
        assert response.json()["user_notes"] == "补充反思"

    def test_delete_review(self, client, db):
        review = create_review_row(db)

        response = client.delete(f"/api/review/{review.id}")

        assert response.status_code == 200
        assert response.json() == {"message": "已删除"}

    def test_get_review_stats(self, client, db):
        create_review_row(db)
        create_review_row(
            db,
            ts_code="000001.SZ",
            stock_name="平安银行",
            overall_score=6.0,
            created_at="2026-04-04T10:00:00Z",
            updated_at="2026-04-04T10:00:00Z",
        )

        response = client.get("/api/review/stats")

        assert response.status_code == 200
        assert response.json()["total_reviews"] == 2

    def test_list_patterns(self, client, db):
        create_pattern_row(db)

        response = client.get("/api/review/patterns")

        assert response.status_code == 200
        assert len(response.json()["patterns"]) == 1

    @patch("app.services.agents.review.run_pattern_agent")
    def test_refresh_patterns(self, mock_run_pattern_agent, client, db):
        create_review_row(db)
        create_review_row(
            db,
            ts_code="000001.SZ",
            stock_name="平安银行",
            created_at="2026-04-04T10:00:00Z",
            updated_at="2026-04-04T10:00:00Z",
        )
        create_review_row(
            db,
            ts_code="600036.SH",
            stock_name="招商银行",
            created_at="2026-04-05T10:00:00Z",
            updated_at="2026-04-05T10:00:00Z",
        )
        mock_run_pattern_agent.return_value = {
            "status": "ok",
            "patterns": [
                {
                    "pattern_type": "strength",
                    "title": "执行稳定",
                    "description": "能按计划执行。",
                    "dimension": "discipline",
                    "evidence_ids": [1, 2],
                }
            ],
        }

        response = client.post("/api/review/patterns/refresh")

        assert response.status_code == 200
        assert response.json()["patterns"][0]["title"] == "执行稳定"

    def test_update_pattern_status(self, client, db):
        pattern = create_pattern_row(db)

        response = client.patch(f"/api/review/patterns/{pattern.id}/status", json={"status": "resolved"})

        assert response.status_code == 200
        assert response.json()["status"] == "resolved"
