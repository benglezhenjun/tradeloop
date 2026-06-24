"""
分析报告 API (V4)

三个端点：
  GET  /api/analysis/llm_status       — LLM 配置状态
  POST /api/analysis/daily_report     — 触发生成日报（同步，需等待 30-90 秒）
  POST /api/analysis/stock/{ts_code}  — 触发单股分析
  GET  /api/analysis/reports          — 查看历史报告列表
  GET  /api/analysis/reports/{id}     — 查看某份历史报告详情
"""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.envelope import list_envelope
from app.database import get_db
from app.models.analysis import AnalysisReport
from app.services import llm
from app.services.agents import (
    run_industry_agent,
    run_market_agent,
    run_report_agent,
    run_screening_agent,
    run_stock_agent,
    run_watchlist_agent,
)

router = APIRouter()


@router.get("/llm_status")
def llm_status():
    """返回当前 LLM 配置状态，前端据此决定是否显示分析功能。"""
    return llm.get_status()


@router.post("/daily_report")
def generate_daily_report(db: Session = Depends(get_db)):
    """
    触发完整日报生成（同步执行，预计 30-90 秒）。

    流程：MarketAgent → IndustryAgent → WatchlistAgent → ScreeningAgent → ReportAgent
    各 Agent 失败不中断整体，失败部分显示错误提示。
    生成后保存到数据库，并返回完整报告内容。
    """
    if not llm.is_configured():
        raise HTTPException(
            status_code=400,
            detail="LLM 未配置，请在 config/local.toml 中填写 [llm] api_key。",
        )

    # 依次运行前 4 个 Agent
    sections = {
        "market": run_market_agent(db),
        "industry": run_industry_agent(db),
        "watchlist": run_watchlist_agent(db),
        "screening": run_screening_agent(db),
    }

    # ReportAgent 汇总
    summary = run_report_agent(sections)
    sections["summary"] = summary

    # 拼接完整报告
    section_titles = {
        "market": "## 市场环境",
        "industry": "## 行业热度",
        "watchlist": "## 自选股动态",
        "screening": "## 策略筛选回顾",
        "summary": "## 综合日报",
    }
    generated_at = datetime.now().isoformat(timespec="seconds")
    full_report = f"# 每日投研日报\n\n生成时间：{generated_at}\n\n"
    full_report += "\n\n".join(
        f"{section_titles[k]}\n\n{v}" for k, v in sections.items()
    )

    # 保存到数据库
    report = AnalysisReport(
        report_type="daily",
        ts_code=None,
        content=full_report,
        sections=json.dumps(sections, ensure_ascii=False),
        generated_at=generated_at,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "id": report.id,
        "report": full_report,
        "sections": sections,
        "generated_at": generated_at,
    }


@router.post("/stock/{ts_code}")
def analyze_stock(ts_code: str, db: Session = Depends(get_db)):
    """
    触发单只股票的深度分析（同步执行，预计 15-40 秒）。
    """
    if not llm.is_configured():
        raise HTTPException(
            status_code=400,
            detail="LLM 未配置，请在 config/local.toml 中填写 [llm] api_key。",
        )

    analysis = run_stock_agent(db, ts_code)
    generated_at = datetime.now().isoformat(timespec="seconds")

    report = AnalysisReport(
        report_type="stock",
        ts_code=ts_code,
        content=analysis,
        sections=None,
        generated_at=generated_at,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "id": report.id,
        "ts_code": ts_code,
        "analysis": analysis,
        "generated_at": generated_at,
    }


@router.get("/reports")
def list_reports(report_type: str | None = None, limit: int = 20, db: Session = Depends(get_db)):
    """
    查看历史报告列表（仅元数据，不返回全文）。
    report_type: "daily" 或 "stock"，不传则返回全部。
    """
    q = db.query(
        AnalysisReport.id,
        AnalysisReport.report_type,
        AnalysisReport.ts_code,
        AnalysisReport.generated_at,
    ).order_by(AnalysisReport.id.desc())

    if report_type:
        q = q.filter(AnalysisReport.report_type == report_type)

    rows = q.limit(limit).all()
    return list_envelope(
        [
            {"id": r.id, "report_type": r.report_type, "ts_code": r.ts_code, "generated_at": r.generated_at}
            for r in rows
        ]
    )


@router.get("/reports/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db)):
    """查看某份历史报告的完整内容。"""
    report = db.get(AnalysisReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    sections = None
    if report.sections:
        try:
            sections = json.loads(report.sections)
        except Exception:
            pass

    return {
        "id": report.id,
        "report_type": report.report_type,
        "ts_code": report.ts_code,
        "content": report.content,
        "sections": sections,
        "generated_at": report.generated_at,
    }
