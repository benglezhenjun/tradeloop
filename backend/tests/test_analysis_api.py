"""
分析报告 API（HTTP 层）测试。

analysis 端点依赖 LLM 与多个 Agent（真实调用需 api_key 且耗时数十秒），
这里全部 mock 掉外部调用，只验证路由装配、未配置时的 400 拦截、
报告落库与历史查询信封。
"""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def client(db):
    from app.api import analysis as analysis_api
    from app.database import get_db

    app = FastAPI()
    # analysis 路由自身无 prefix，生产在 main.py 以 /api/analysis 挂载
    app.include_router(analysis_api.router, prefix="/api/analysis")

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _seed_report(db, report_type="daily", ts_code=None, content="正文", sections=None):
    from app.models.analysis import AnalysisReport

    report = AnalysisReport(
        report_type=report_type,
        ts_code=ts_code,
        content=content,
        sections=sections,
        generated_at="2026-06-24T10:00:00",
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


# ---- llm_status ----

def test_llm_status_passthrough(client):
    with patch("app.services.llm.get_status", return_value={"configured": False, "model": "deepseek-chat"}):
        resp = client.get("/api/analysis/llm_status")
    assert resp.status_code == 200
    assert resp.json() == {"configured": False, "model": "deepseek-chat"}


# ---- daily_report ----

def test_daily_report_blocked_when_unconfigured(client):
    with patch("app.services.llm.is_configured", return_value=False):
        resp = client.post("/api/analysis/daily_report")
    assert resp.status_code == 400
    assert "LLM" in resp.json()["detail"]


def test_daily_report_success_saves_and_returns(client, db):
    with (
        patch("app.services.llm.is_configured", return_value=True),
        patch("app.api.analysis.run_market_agent", return_value="市场段落"),
        patch("app.api.analysis.run_industry_agent", return_value="行业段落"),
        patch("app.api.analysis.run_watchlist_agent", return_value="自选段落"),
        patch("app.api.analysis.run_screening_agent", return_value="筛选段落"),
        patch("app.api.analysis.run_report_agent", return_value="综合段落"),
    ):
        resp = client.post("/api/analysis/daily_report")

    assert resp.status_code == 200
    body = resp.json()
    assert "市场段落" in body["report"]
    assert body["sections"]["summary"] == "综合段落"

    # 已落库，可在历史列表查到
    listed = client.get("/api/analysis/reports").json()
    assert listed["total"] == 1
    assert listed["items"][0]["report_type"] == "daily"


# ---- analyze_stock ----

def test_analyze_stock_blocked_when_unconfigured(client):
    with patch("app.services.llm.is_configured", return_value=False):
        resp = client.post("/api/analysis/stock/600000.SH")
    assert resp.status_code == 400


def test_analyze_stock_success(client):
    with (
        patch("app.services.llm.is_configured", return_value=True),
        patch("app.api.analysis.run_stock_agent", return_value="个股深度分析正文"),
    ):
        resp = client.post("/api/analysis/stock/600000.SH")

    assert resp.status_code == 200
    body = resp.json()
    assert body["ts_code"] == "600000.SH"
    assert body["analysis"] == "个股深度分析正文"


# ---- 历史报告 ----

def test_list_reports_filter_by_type(client, db):
    _seed_report(db, report_type="daily")
    _seed_report(db, report_type="stock", ts_code="600000.SH")

    all_reports = client.get("/api/analysis/reports").json()
    assert all_reports["total"] == 2

    stock_only = client.get("/api/analysis/reports", params={"report_type": "stock"}).json()
    assert stock_only["total"] == 1
    assert stock_only["items"][0]["ts_code"] == "600000.SH"


def test_get_report_detail(client, db):
    report = _seed_report(db, content="完整正文")
    resp = client.get(f"/api/analysis/reports/{report.id}")
    assert resp.status_code == 200
    assert resp.json()["content"] == "完整正文"


def test_get_report_detail_parses_sections_json(client, db):
    report = _seed_report(db, sections='{"market": "段落"}')
    body = client.get(f"/api/analysis/reports/{report.id}").json()
    assert body["sections"] == {"market": "段落"}


def test_get_report_404(client):
    resp = client.get("/api/analysis/reports/99999")
    assert resp.status_code == 404
