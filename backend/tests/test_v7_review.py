import json
from unittest.mock import patch

import pytest
from sqlalchemy import text


def insert_stock(db, ts_code: str, name: str):
    db.execute(
        text(
            "INSERT OR IGNORE INTO stock_basic "
            "(ts_code, name, industry, market, list_date, list_status) "
            "VALUES (:ts_code, :name, '银行', '主板', '20200101', 'L')"
        ),
        {"ts_code": ts_code, "name": name},
    )
    db.commit()


def insert_quotes(db, ts_code: str, start_date: str, closes: list[float]):
    from datetime import datetime, timedelta

    current = datetime.strptime(start_date, "%Y-%m-%d")
    for idx, close in enumerate(closes):
        trade_date = (current + timedelta(days=idx)).strftime("%Y%m%d")
        db.execute(
            text(
                "INSERT OR IGNORE INTO daily_quote "
                "(ts_code, trade_date, open, high, low, close, vol, amount, pct_chg, total_mv, turnover_rate) "
                "VALUES (:ts_code, :trade_date, :open, :high, :low, :close, 1000, 200000, 0.5, 500000, 1.0)"
            ),
            {
                "ts_code": ts_code,
                "trade_date": trade_date,
                "open": close - 0.2,
                "high": close + 0.3,
                "low": close - 0.4,
                "close": close,
            },
        )
    db.commit()


def sample_plan_data(**overrides):
    data = {
        "ts_code": "600000.SH",
        "stock_name": "浦发银行",
        "direction": "buy",
        "target_price": 10.5,
        "stop_loss_price": 9.5,
        "take_profit": [{"price": 12.0, "ratio": 1.0, "note": "全部"}],
        "position_ratio": 0.2,
        "reasoning": "测试计划",
        "source": "manual",
    }
    data.update(overrides)
    return data


def sample_scores(**overrides):
    scores = {
        "entry_timing": 7,
        "exit_timing": 8,
        "stop_loss": 6,
        "take_profit": 7,
        "position_sizing": 8,
        "holding_period": 6,
        "discipline": 7,
        "risk_reward": 8,
    }
    scores.update(overrides)
    return scores


def sample_llm_result(**overrides):
    result = {
        "scores": sample_scores(),
        "analysis": "综合复盘分析",
        "improvement": "后续改进建议",
    }
    result.update(overrides)
    return result


def prepare_trade_cycle(db, *, ts_code: str = "600000.SH", stock_name: str = "浦发银行", plan_id: int | None = None):
    from app.services import trade as trade_service
    from app.services import user_config

    insert_stock(db, ts_code, stock_name)
    insert_quotes(db, ts_code, "2026-03-22", [9.8, 9.9, 10.0, 10.3, 10.8, 11.2, 11.6, 12.0, 12.1, 12.2])
    user_config.set_config(db, "total_capital", "500000")

    buy_result = trade_service.create_trade(
        db,
        {
            "ts_code": ts_code,
            "stock_name": stock_name,
            "direction": "buy",
            "price": 10.0,
            "quantity": 100,
            "trade_date": "2026-04-01",
            "fee": 0.0,
            "plan_id": plan_id,
        },
    )
    assert "error" not in buy_result

    sell_result = trade_service.create_trade(
        db,
        {
            "ts_code": ts_code,
            "stock_name": stock_name,
            "direction": "sell",
            "price": 12.0,
            "quantity": 100,
            "trade_date": "2026-04-03",
            "fee": 0.0,
            "plan_id": plan_id,
        },
    )
    assert "error" not in sell_result


def create_plan(db, **overrides):
    from app.services import plan as plan_service

    result = plan_service.create_plan(db, sample_plan_data(**overrides))
    assert "error" not in result
    return result


def create_review_row(db, **overrides):
    from app.models.review import TradeReview

    data = {
        "ts_code": "600000.SH",
        "stock_name": "浦发银行",
        "plan_id": None,
        "total_buy_amount": 1000.0,
        "total_sell_amount": 1200.0,
        "total_fee": 0.0,
        "realized_pnl": 200.0,
        "trade_count": 2,
        "first_trade_date": "2026-04-01",
        "last_trade_date": "2026-04-03",
        "holding_days": 2,
        "scores": json.dumps(sample_scores(), ensure_ascii=False),
        "overall_score": 7.1,
        "analysis": "分析",
        "improvement": "改进",
        "user_notes": None,
        "created_at": "2026-04-03T10:00:00Z",
        "updated_at": "2026-04-03T10:00:00Z",
    }
    data.update(overrides)
    review = TradeReview(**data)
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def create_pattern_row(db, **overrides):
    from app.models.review import BehaviorPattern

    data = {
        "pattern_type": "strength",
        "title": "执行稳定",
        "description": "能按计划执行交易",
        "dimension": "discipline",
        "evidence_ids": json.dumps([1, 2], ensure_ascii=False),
        "status": "active",
        "created_at": "2026-04-03T10:00:00Z",
        "updated_at": "2026-04-03T10:00:00Z",
    }
    data.update(overrides)
    pattern = BehaviorPattern(**data)
    db.add(pattern)
    db.commit()
    db.refresh(pattern)
    return pattern


class TestReviewService:
    def test_build_review_context_returns_context(self, db):
        from app.services import review as review_service

        plan = create_plan(db)
        prepare_trade_cycle(db, plan_id=plan["id"])

        context = review_service.build_review_context(db, "600000.SH")

        assert context is not None
        assert context["ts_code"] == "600000.SH"
        assert context["stock_name"] == "浦发银行"
        assert context["plan"]["id"] == plan["id"]
        assert context["trade_count"] == 2
        assert context["total_buy_amount"] == pytest.approx(1000.0, rel=1e-6)
        assert context["total_sell_amount"] == pytest.approx(1200.0, rel=1e-6)
        assert context["realized_pnl"] == pytest.approx(200.0, rel=1e-6)
        assert context["holding_days"] == 2
        assert context["total_capital"] == 500000.0
        assert len(context["trades"]) == 2
        assert len(context["quotes"]) > 0

    def test_build_review_context_returns_none_when_no_trade(self, db):
        from app.services import review as review_service

        insert_stock(db, "600000.SH", "浦发银行")

        assert review_service.build_review_context(db, "600000.SH") is None

    def test_create_review_success(self, db):
        from app.services import review as review_service

        prepare_trade_cycle(db)

        result = review_service.create_review(db, "600000.SH", sample_llm_result())

        assert "error" not in result
        assert result["ts_code"] == "600000.SH"
        assert result["scores"]["entry_timing"] == 7
        assert result["overall_score"] == 7.1
        assert result["trade_count"] == 2

    def test_create_review_rejects_out_of_range_scores(self, db):
        from app.services import review as review_service

        prepare_trade_cycle(db)

        result = review_service.create_review(
            db,
            "600000.SH",
            sample_llm_result(scores=sample_scores(entry_timing=11)),
        )

        assert "error" in result

    def test_create_review_rejects_missing_dimension(self, db):
        from app.services import review as review_service

        prepare_trade_cycle(db)
        bad_scores = sample_scores()
        bad_scores.pop("discipline")

        result = review_service.create_review(
            db,
            "600000.SH",
            sample_llm_result(scores=bad_scores),
        )

        assert "error" in result

    def test_list_reviews_returns_descending(self, db):
        from app.services import review as review_service

        create_review_row(db, ts_code="000001.SZ", stock_name="平安银行", created_at="2026-04-01T10:00:00Z")
        create_review_row(db, ts_code="600000.SH", stock_name="浦发银行", created_at="2026-04-03T10:00:00Z")

        result = review_service.list_reviews(db)

        assert [item["ts_code"] for item in result["reviews"]] == ["600000.SH", "000001.SZ"]

    def test_list_reviews_filters_by_ts_code(self, db):
        from app.services import review as review_service

        create_review_row(db, ts_code="000001.SZ", stock_name="平安银行")
        create_review_row(db, ts_code="600000.SH", stock_name="浦发银行")

        result = review_service.list_reviews(db, ts_code="000001.SZ")

        assert len(result["reviews"]) == 1
        assert result["reviews"][0]["ts_code"] == "000001.SZ"

    def test_get_review_detail_returns_detail(self, db):
        from app.services import review as review_service

        review = create_review_row(db)

        result = review_service.get_review_detail(db, review.id)

        assert result is not None
        assert result["id"] == review.id

    def test_get_review_detail_returns_none_for_missing(self, db):
        from app.services import review as review_service

        assert review_service.get_review_detail(db, 999) is None

    def test_update_review_notes_updates_notes(self, db):
        from app.services import review as review_service

        review = create_review_row(db)

        result = review_service.update_review_notes(db, review.id, "新的复盘反思")

        assert result["user_notes"] == "新的复盘反思"

    def test_delete_review_success(self, db):
        from app.services import review as review_service

        review = create_review_row(db)

        result = review_service.delete_review(db, review.id)

        assert result == {"message": "已删除"}
        assert review_service.get_review_detail(db, review.id) is None

    def test_delete_review_returns_error_for_missing(self, db):
        from app.services import review as review_service

        result = review_service.delete_review(db, 999)

        assert "error" in result

    def test_get_review_stats_calculates_averages(self, db):
        from app.services import review as review_service

        create_review_row(
            db,
            scores=json.dumps(sample_scores(entry_timing=8, exit_timing=9, risk_reward=9), ensure_ascii=False),
            overall_score=7.5,
            realized_pnl=300.0,
        )
        create_review_row(
            db,
            ts_code="000001.SZ",
            stock_name="平安银行",
            scores=json.dumps(sample_scores(entry_timing=4, exit_timing=8, risk_reward=1), ensure_ascii=False),
            overall_score=5.5,
            realized_pnl=-100.0,
            created_at="2026-04-04T10:00:00Z",
            updated_at="2026-04-04T10:00:00Z",
        )

        result = review_service.get_review_stats(db)

        assert result["total_reviews"] == 2
        assert result["avg_overall_score"] == 6.5
        assert result["avg_scores"]["entry_timing"] == 6.0
        assert result["best_dimension"] == "exit_timing"
        assert result["worst_dimension"] == "risk_reward"
        assert result["win_count"] == 1
        assert result["loss_count"] == 1
        assert result["total_reviewed_pnl"] == 200.0


class TestPatternService:
    def test_save_patterns_replaces_old_active_patterns(self, db):
        from app.services import pattern as pattern_service

        create_pattern_row(db, title="旧模式")

        result = pattern_service.save_patterns(
            db,
            [
                {
                    "pattern_type": "weakness",
                    "title": "追涨",
                    "description": "容易在上涨后追高买入",
                    "dimension": "discipline",
                    "evidence_ids": [1, 2],
                }
            ],
        )

        assert len(result["patterns"]) == 1
        assert result["patterns"][0]["title"] == "追涨"
        assert pattern_service.list_patterns(db)["patterns"][0]["title"] == "追涨"

    def test_list_patterns_filters_by_status(self, db):
        from app.services import pattern as pattern_service

        create_pattern_row(db, status="active")
        create_pattern_row(db, title="已解决", status="resolved", updated_at="2026-04-04T10:00:00Z")

        result = pattern_service.list_patterns(db, status="resolved")

        assert len(result["patterns"]) == 1
        assert result["patterns"][0]["status"] == "resolved"

    def test_update_pattern_status_success(self, db):
        from app.services import pattern as pattern_service

        pattern = create_pattern_row(db)

        result = pattern_service.update_pattern_status(db, pattern.id, "resolved")

        assert result["status"] == "resolved"

    def test_update_pattern_status_rejects_invalid_status(self, db):
        from app.services import pattern as pattern_service

        pattern = create_pattern_row(db)

        result = pattern_service.update_pattern_status(db, pattern.id, "archived")

        assert "error" in result


class TestReviewAgent:
    def test_run_review_agent_returns_error_when_no_trade(self, db):
        from app.services.agents.review import run_review_agent

        insert_stock(db, "600000.SH", "浦发银行")

        result = run_review_agent(db, "600000.SH")

        assert "error" in result

    @patch("app.services.agents.review._safe_llm_call")
    def test_run_review_agent_success(self, mock_safe_llm_call, db):
        from app.services.agents.review import run_review_agent

        prepare_trade_cycle(db)
        mock_safe_llm_call.return_value = json.dumps(sample_llm_result(), ensure_ascii=False)

        result = run_review_agent(db, "600000.SH")

        assert result["status"] == "ok"
        assert result["scores"]["entry_timing"] == 7
        assert result["analysis"] == "综合复盘分析"

    @patch("app.services.agents.review._safe_llm_call")
    def test_run_review_agent_rejects_invalid_scores(self, mock_safe_llm_call, db):
        from app.services.agents.review import run_review_agent

        prepare_trade_cycle(db)
        mock_safe_llm_call.return_value = json.dumps(
            sample_llm_result(scores=sample_scores(entry_timing=99)),
            ensure_ascii=False,
        )

        result = run_review_agent(db, "600000.SH")

        assert "error" in result

    @patch("app.services.agents.review._safe_llm_call")
    def test_run_review_agent_repairs_incompatible_json_shape(self, mock_safe_llm_call, db):
        from app.services.agents.review import run_review_agent

        prepare_trade_cycle(db)
        mock_safe_llm_call.side_effect = [
            json.dumps(
                {
                    "analysis": {
                        "trade_summary": {"symbol": "600000.SH"},
                        "performance_evaluation": {
                            "entry_timing": "良好",
                            "exit_timing": "良好",
                            "overall_rating": "整体尚可",
                        },
                        "suggestions": ["补充交易计划", "明确止损规则"],
                    }
                },
                ensure_ascii=False,
            ),
            json.dumps(sample_llm_result(), ensure_ascii=False),
        ]

        result = run_review_agent(db, "600000.SH")

        assert result["status"] == "ok"
        assert result["scores"]["entry_timing"] == 7
        assert mock_safe_llm_call.call_count == 2

    def test_run_pattern_agent_requires_at_least_three_reviews(self, db):
        from app.services.agents.review import run_pattern_agent

        create_review_row(db)
        create_review_row(db, ts_code="000001.SZ", stock_name="平安银行")

        result = run_pattern_agent(db)

        assert "error" in result

    @patch("app.services.agents.review._safe_llm_call")
    def test_run_pattern_agent_success(self, mock_safe_llm_call, db):
        from app.services.agents.review import run_pattern_agent

        create_review_row(db, id=None)
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
        mock_safe_llm_call.return_value = json.dumps(
            [
                {
                    "pattern_type": "strength",
                    "title": "执行稳定",
                    "description": "多数时候能按计划执行。",
                    "dimension": "discipline",
                    "evidence_ids": [1, 2],
                }
            ],
            ensure_ascii=False,
        )

        result = run_pattern_agent(db)

        assert result["status"] == "ok"
        assert len(result["patterns"]) == 1
        assert result["patterns"][0]["title"] == "执行稳定"

    @patch("app.services.agents.review._safe_llm_call")
    def test_run_pattern_agent_repairs_incompatible_json_shape(self, mock_safe_llm_call, db):
        from app.services.agents.review import run_pattern_agent

        create_review_row(db, id=None)
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
        mock_safe_llm_call.side_effect = [
            json.dumps(
                {
                    "overall_assessment": {"average_score": 6.7},
                    "strengths": ["执行较稳定"],
                    "weaknesses": ["止损不够坚决"],
                    "actionable_advice": ["补强止损纪律"],
                },
                ensure_ascii=False,
            ),
            json.dumps(
                [
                    {
                        "pattern_type": "strength",
                        "title": "执行稳定",
                        "description": "多数时候能按计划执行。",
                        "dimension": "discipline",
                        "evidence_ids": [1, 2],
                    },
                    {
                        "pattern_type": "weakness",
                        "title": "止损偏慢",
                        "description": "部分交易止损动作偏慢。",
                        "dimension": "stop_loss",
                        "evidence_ids": [3],
                    },
                ],
                ensure_ascii=False,
            ),
        ]

        result = run_pattern_agent(db)

        assert result["status"] == "ok"
        assert len(result["patterns"]) == 2
        assert mock_safe_llm_call.call_count == 2
