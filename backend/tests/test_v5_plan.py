"""
V5 交易计划测试

测试覆盖：
- UserConfig 读写
- TradingPlan CRUD（创建、查询、编辑、状态变更、删除）
- 数据校验（仓位上限、止盈 ratio 之和、状态流转）
- PlanAgent mock（prompt 构造 + JSON 解析 + 解析失败降级）
"""

import json
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client(db):
    from app.api import plan as plan_api
    from app.api import user_config as config_api

    app = FastAPI()
    app.include_router(plan_api.router, prefix="/api")
    app.include_router(config_api.router, prefix="/api")

    def override_get_db():
        yield db

    app.dependency_overrides[plan_api.get_db] = override_get_db
    app.dependency_overrides[config_api.get_db] = override_get_db

    return TestClient(app)


def insert_stock(db, ts_code="000001.SZ", name="平安银行", industry="银行"):
    db.execute(
        text(
            "INSERT OR IGNORE INTO stock_basic "
            "(ts_code, name, industry, market, list_date, list_status) "
            "VALUES (:ts_code, :name, :industry, '主板', '20200101', 'L')"
        ),
        {"ts_code": ts_code, "name": name, "industry": industry},
    )
    db.commit()


def insert_quotes(db, ts_code="000001.SZ", count=60):
    for i in range(count):
        date = f"2026{(3 - i // 30):02d}{(28 - i % 28):02d}"
        db.execute(
            text(
                "INSERT OR IGNORE INTO daily_quote "
                "(ts_code, trade_date, open, high, low, close, vol, amount, pct_chg, total_mv, turnover_rate) "
                "VALUES (:tc, :td, 10.0, 10.5, 9.5, :close, 1000, 200000, 0.5, 500000, 1.0)"
            ),
            {"tc": ts_code, "td": date, "close": 10.0 + i * 0.05},
        )
    db.commit()


def _sample_plan_data(**overrides):
    data = {
        "ts_code": "000001.SZ",
        "stock_name": "平安银行",
        "direction": "buy",
        "target_price": 12.50,
        "stop_loss_price": 11.80,
        "take_profit": [
            {"price": 13.5, "ratio": 0.5, "note": "第一档"},
            {"price": 14.5, "ratio": 0.5, "note": "第二档"},
        ],
        "position_ratio": 0.2,
        "reasoning": "测试计划理由",
        "source": "manual",
    }
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# UserConfig
# ---------------------------------------------------------------------------

class TestUserConfig:
    def test_get_nonexistent_returns_none(self, db):
        from app.services.user_config import get_config
        assert get_config(db, "nonexistent") is None

    def test_total_capital_default_is_zero(self, db):
        from app.services.user_config import get_config
        assert get_config(db, "total_capital") == "0"

    def test_set_and_get(self, db):
        from app.services.user_config import get_config, set_config
        set_config(db, "total_capital", "500000")
        assert get_config(db, "total_capital") == "500000"

    def test_update_existing(self, db):
        from app.services.user_config import get_config, set_config
        set_config(db, "total_capital", "500000")
        set_config(db, "total_capital", "800000")
        assert get_config(db, "total_capital") == "800000"


# ---------------------------------------------------------------------------
# Plan CRUD
# ---------------------------------------------------------------------------

class TestPlanCreate:
    def test_create_success(self, db):
        from app.services.plan import create_plan
        result = create_plan(db, _sample_plan_data())
        assert "id" in result
        assert result["status"] == "pending"
        assert result["stock_name"] == "平安银行"
        assert len(result["take_profit"]) == 2

    def test_position_ratio_over_limit(self, db):
        from app.services.plan import create_plan
        result = create_plan(db, _sample_plan_data(position_ratio=0.5))
        assert "error" in result

    def test_position_ratio_zero(self, db):
        from app.services.plan import create_plan
        result = create_plan(db, _sample_plan_data(position_ratio=0))
        assert "error" in result

    def test_invalid_direction(self, db):
        from app.services.plan import create_plan
        result = create_plan(db, _sample_plan_data(direction="hold"))
        assert "error" in result

    def test_take_profit_ratio_sum_not_one(self, db):
        from app.services.plan import create_plan
        result = create_plan(db, _sample_plan_data(
            take_profit=[{"price": 13.5, "ratio": 0.3}, {"price": 14.5, "ratio": 0.3}]
        ))
        assert "error" in result

    def test_take_profit_empty(self, db):
        from app.services.plan import create_plan
        result = create_plan(db, _sample_plan_data(take_profit=[]))
        assert "error" in result

    def test_create_with_alternatives(self, db):
        from app.services.plan import create_plan, get_plan_detail
        alts = [{"tier_label": "aggressive", "target_price": 11.0}]
        result = create_plan(db, _sample_plan_data(
            source="llm_generated", alternatives=alts
        ))
        detail = get_plan_detail(db, result["id"])
        assert detail is not None
        assert detail["alternatives"] == alts


class TestPlanQuery:
    def test_list_empty(self, db):
        from app.services.plan import get_plans
        assert get_plans(db) == []

    def test_list_and_filter(self, db):
        from app.services.plan import create_plan, get_plans
        create_plan(db, _sample_plan_data())
        create_plan(db, _sample_plan_data(ts_code="600036.SH", stock_name="招商银行"))
        assert len(get_plans(db)) == 2
        assert len(get_plans(db, ts_code="000001.SZ")) == 1
        assert len(get_plans(db, status="executed")) == 0

    def test_detail_not_found(self, db):
        from app.services.plan import get_plan_detail
        assert get_plan_detail(db, 999) is None


class TestPlanUpdate:
    def test_update_fields(self, db):
        from app.services.plan import create_plan, update_plan
        p = create_plan(db, _sample_plan_data())
        result = update_plan(db, p["id"], {"target_price": 13.00, "position_ratio": 0.3})
        assert result["target_price"] == 13.0
        assert result["position_ratio"] == 0.3

    def test_update_nonexistent(self, db):
        from app.services.plan import update_plan
        result = update_plan(db, 999, {"target_price": 13.00})
        assert "error" in result

    def test_update_executed_blocked(self, db):
        from app.services.plan import create_plan, update_plan, update_plan_status
        p = create_plan(db, _sample_plan_data())
        update_plan_status(db, p["id"], "executed")
        result = update_plan(db, p["id"], {"target_price": 15.00})
        assert "error" in result

    def test_update_take_profit(self, db):
        from app.services.plan import create_plan, update_plan
        p = create_plan(db, _sample_plan_data())
        new_tp = [{"price": 15.0, "ratio": 1.0, "note": "全部"}]
        result = update_plan(db, p["id"], {"take_profit": new_tp})
        assert len(result["take_profit"]) == 1


class TestPlanStatus:
    def test_pending_to_executed(self, db):
        from app.services.plan import create_plan, update_plan_status
        p = create_plan(db, _sample_plan_data())
        result = update_plan_status(db, p["id"], "executed")
        assert result["status"] == "executed"

    def test_pending_to_abandoned(self, db):
        from app.services.plan import create_plan, update_plan_status
        p = create_plan(db, _sample_plan_data())
        result = update_plan_status(db, p["id"], "abandoned")
        assert result["status"] == "abandoned"

    def test_reverse_blocked(self, db):
        from app.services.plan import create_plan, update_plan_status
        p = create_plan(db, _sample_plan_data())
        update_plan_status(db, p["id"], "executed")
        result = update_plan_status(db, p["id"], "pending")
        assert "error" in result

    def test_executed_to_abandoned_blocked(self, db):
        from app.services.plan import create_plan, update_plan_status
        p = create_plan(db, _sample_plan_data())
        update_plan_status(db, p["id"], "executed")
        result = update_plan_status(db, p["id"], "abandoned")
        assert "error" in result


class TestPlanDelete:
    def test_delete_success(self, db):
        from app.services.plan import create_plan, delete_plan, get_plans
        p = create_plan(db, _sample_plan_data())
        assert delete_plan(db, p["id"]) is True
        assert len(get_plans(db)) == 0

    def test_delete_nonexistent(self, db):
        from app.services.plan import delete_plan
        assert delete_plan(db, 999) is False


# ---------------------------------------------------------------------------
# PlanAgent (mock LLM)
# ---------------------------------------------------------------------------

_MOCK_LLM_RESPONSE = json.dumps([
    {
        "tier_label": "aggressive",
        "direction": "buy",
        "target_price": 10.5,
        "stop_loss_price": 9.8,
        "take_profit": [{"price": 11.5, "ratio": 0.5, "note": "第一档"}, {"price": 12.5, "ratio": 0.5, "note": "第二档"}],
        "position_ratio": 0.35,
        "reasoning": "激进方案理由",
        "risk_comment": "波动风险较大",
    },
    {
        "tier_label": "balanced",
        "direction": "buy",
        "target_price": 10.2,
        "stop_loss_price": 9.5,
        "take_profit": [{"price": 11.0, "ratio": 0.4, "note": "第一档"}, {"price": 12.0, "ratio": 0.6, "note": "第二档"}],
        "position_ratio": 0.25,
        "reasoning": "稳健方案理由",
        "risk_comment": "风险中等",
    },
    {
        "tier_label": "conservative",
        "direction": "buy",
        "target_price": 9.8,
        "stop_loss_price": 9.2,
        "take_profit": [{"price": 10.5, "ratio": 1.0, "note": "统一止盈"}],
        "position_ratio": 0.15,
        "reasoning": "保守方案理由",
        "risk_comment": "风险较低",
    },
])


class TestPlanAgent:
    def test_stock_not_found(self, db):
        from app.services.agents import run_plan_agent
        result = run_plan_agent(db, "999999.SZ", 500000)
        assert "error" in result

    def test_no_quotes(self, db):
        from app.services.agents import run_plan_agent
        insert_stock(db)
        result = run_plan_agent(db, "000001.SZ", 500000)
        assert "error" in result

    @patch("app.services.agents.llm.chat")
    @patch("app.services.agents.get_market_overview")
    def test_success(self, mock_market, mock_chat, db):
        from app.services.agents import run_plan_agent
        insert_stock(db)
        insert_quotes(db)

        mock_market.return_value = {
            "trade_date": "20260406",
            "up_count": 2500, "down_count": 1800, "flat_count": 200,
            "limit_up_count": 50, "limit_down_count": 5,
            "total_amount_yi": 8000, "avg_pct_chg": 0.5,
        }
        mock_chat.return_value = _MOCK_LLM_RESPONSE

        result = run_plan_agent(db, "000001.SZ", 500000)
        assert "plans" in result
        assert len(result["plans"]) == 3
        # 验证已补充股票信息
        assert result["plans"][0]["ts_code"] == "000001.SZ"
        assert result["plans"][0]["stock_name"] == "平安银行"

    @patch("app.services.agents.llm.chat")
    @patch("app.services.agents.get_market_overview")
    def test_json_parse_failure(self, mock_market, mock_chat, db):
        from app.services.agents import run_plan_agent
        insert_stock(db)
        insert_quotes(db)

        mock_market.return_value = {"trade_date": None}
        mock_chat.return_value = "这不是一个JSON"

        result = run_plan_agent(db, "000001.SZ", 500000)
        assert result["status"] == "manual_fallback"
        assert "JSON" in result["message"]
        assert result["prefill"]["ts_code"] == "000001.SZ"

    @patch("app.services.agents.llm.chat")
    @patch("app.services.agents.get_market_overview")
    def test_markdown_wrapped_json(self, mock_market, mock_chat, db):
        from app.services.agents import run_plan_agent
        insert_stock(db)
        insert_quotes(db)

        mock_market.return_value = {"trade_date": None}
        mock_chat.return_value = f"```json\n{_MOCK_LLM_RESPONSE}\n```"

        result = run_plan_agent(db, "000001.SZ", 500000)
        assert result["status"] == "ok"
        assert "plans" in result
        assert len(result["plans"]) == 3

    @patch("app.services.agents.llm.chat")
    @patch("app.services.agents.get_market_overview")
    def test_json_with_preamble_and_code_block_parses(self, mock_market, mock_chat, db):
        from app.services.agents import run_plan_agent
        insert_stock(db)
        insert_quotes(db)

        mock_market.return_value = {"trade_date": None}
        mock_chat.return_value = f"下面是结果：\n```json\n{_MOCK_LLM_RESPONSE}\n```"

        result = run_plan_agent(db, "000001.SZ", 500000)
        assert result["status"] == "ok"
        assert len(result["plans"]) == 3

    @patch("app.services.agents.llm.chat")
    @patch("app.services.agents.get_market_overview")
    def test_llm_exception(self, mock_market, mock_chat, db):
        from app.services.agents import run_plan_agent
        insert_stock(db)
        insert_quotes(db)

        mock_market.return_value = {"trade_date": None}
        mock_chat.side_effect = Exception("API timeout")

        result = run_plan_agent(db, "000001.SZ", 500000)
        assert "error" in result
        assert "timeout" in result["error"]

    @patch("app.services.agents.llm.chat")
    @patch("app.services.agents.get_market_overview")
    def test_invalid_but_parseable_json_returns_manual_fallback(self, mock_market, mock_chat, db):
        from app.services.agents import run_plan_agent
        insert_stock(db)
        insert_quotes(db)

        bad_response = json.dumps([
            {
                "tier_label": "aggressive",
                "direction": "buy",
                "target_price": 10.5,
                "stop_loss_price": 9.8,
                "take_profit": [{"price": 11.5, "ratio": 0.5}, {"price": 12.5, "ratio": 0.5}],
                "position_ratio": 0.5,
                "reasoning": "仓位过高",
                "risk_comment": "风险大",
            },
            {
                "tier_label": "balanced",
                "direction": "buy",
                "target_price": 10.2,
                "stop_loss_price": 9.5,
                "take_profit": [{"price": 11.0, "ratio": 0.4}, {"price": 12.0, "ratio": 0.6}],
                "position_ratio": 0.25,
                "reasoning": "稳健方案",
                "risk_comment": "中风险",
            },
            {
                "tier_label": "conservative",
                "direction": "buy",
                "target_price": 9.8,
                "stop_loss_price": 9.2,
                "take_profit": [{"price": 10.5, "ratio": 1.0}],
                "position_ratio": 0.15,
                "reasoning": "保守方案",
                "risk_comment": "低风险",
            },
        ])

        mock_market.return_value = {"trade_date": None}
        mock_chat.return_value = bad_response

        result = run_plan_agent(db, "000001.SZ", 500000)
        assert result["status"] == "manual_fallback"
        assert result["prefill"]["ts_code"] == "000001.SZ"

    @patch("app.services.agents.llm.chat")
    @patch("app.services.agents.get_market_overview")
    def test_extract_json_from_wrapped_text(self, mock_market, mock_chat, db):
        from app.services.agents import run_plan_agent
        insert_stock(db)
        insert_quotes(db)

        mock_market.return_value = {"trade_date": None}
        mock_chat.return_value = f"以下是结果：\n```json\n{_MOCK_LLM_RESPONSE}\n```\n请查收"

        result = run_plan_agent(db, "000001.SZ", 500000)
        assert "plans" in result
        assert len(result["plans"]) == 3

    @patch("app.services.agents.llm.chat")
    @patch("app.services.agents.get_market_overview")
    def test_invalid_proposal_enters_manual_fallback(self, mock_market, mock_chat, db):
        from app.services.agents import run_plan_agent
        insert_stock(db)
        insert_quotes(db)

        invalid_plans = json.dumps([
            {
                "tier_label": "aggressive",
                "direction": "buy",
                "target_price": 10.5,
                "stop_loss_price": 9.8,
                "take_profit": [{"price": 11.5, "ratio": 0.5}, {"price": 12.5, "ratio": 0.5}],
                "position_ratio": 0.6,
                "reasoning": "激进方案理由",
                "risk_comment": "波动风险较大",
            },
            {
                "tier_label": "balanced",
                "direction": "buy",
                "target_price": 10.2,
                "stop_loss_price": 9.5,
                "take_profit": [{"price": 11.0, "ratio": 0.4}, {"price": 12.0, "ratio": 0.6}],
                "position_ratio": 0.25,
                "reasoning": "稳健方案理由",
                "risk_comment": "风险中等",
            },
            {
                "tier_label": "conservative",
                "direction": "buy",
                "target_price": 9.8,
                "stop_loss_price": 9.2,
                "take_profit": [{"price": 10.5, "ratio": 1.0}],
                "position_ratio": 0.15,
                "reasoning": "保守方案理由",
                "risk_comment": "风险较低",
            },
        ])

        mock_market.return_value = {"trade_date": None}
        mock_chat.return_value = invalid_plans

        result = run_plan_agent(db, "000001.SZ", 500000)
        assert result["status"] == "manual_fallback"
        assert "prefill" in result
        assert result["prefill"]["ts_code"] == "000001.SZ"


class TestPlanApi:
    def test_get_total_capital_returns_zero_default(self, client):
        response = client.get("/api/config/total_capital")

        assert response.status_code == 200
        assert response.json() == {"key": "total_capital", "value": "0"}

    def test_create_plan_returns_201(self, client):
        response = client.post("/api/plan", json=_sample_plan_data())

        assert response.status_code == 201
        assert response.json()["status"] == "pending"

    def test_update_nonexistent_returns_404(self, client):
        response = client.put("/api/plan/999", json={"target_price": 13.0})

        assert response.status_code == 404

    def test_status_nonexistent_returns_404(self, client):
        response = client.patch("/api/plan/999/status", json={"status": "executed"})

        assert response.status_code == 404

    @patch("app.api.plan.run_plan_agent")
    def test_generate_stock_not_found_returns_404(self, mock_run_plan_agent, client):
        client.put("/api/config/total_capital", json={"value": "500000"})
        mock_run_plan_agent.return_value = {"error": "未找到股票 999999.SZ", "error_type": "not_found"}

        response = client.post("/api/plan/generate/999999.SZ")

        assert response.status_code == 404

    @patch("app.api.plan.run_plan_agent")
    def test_generate_upstream_timeout_returns_502(self, mock_run_plan_agent, client):
        client.put("/api/config/total_capital", json={"value": "500000"})
        mock_run_plan_agent.return_value = {"error": "方案生成失败：API timeout", "error_type": "upstream"}

        response = client.post("/api/plan/generate/000001.SZ")

        assert response.status_code == 502

    @patch("app.api.plan.run_plan_agent")
    def test_generate_manual_fallback_returns_200(self, mock_run_plan_agent, client):
        client.put("/api/config/total_capital", json={"value": "500000"})
        mock_run_plan_agent.return_value = {
            "status": "manual_fallback",
            "message": "LLM 返回的内容无法解析为 JSON，请手动创建",
            "prefill": {"ts_code": "000001.SZ", "stock_name": "平安银行"},
            "raw_response": "not-json",
        }

        response = client.post("/api/plan/generate/000001.SZ")

        assert response.status_code == 200
        assert response.json()["status"] == "manual_fallback"
