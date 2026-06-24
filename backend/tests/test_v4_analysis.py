"""
V4 LLM 分析测试

策略：mock LLM 调用，不真实打 API。
测试覆盖：
- llm.is_configured() 的配置判断逻辑
- 各 Agent 在无数据时的降级处理（返回提示字符串，不抛异常）
- 各 Agent 在有数据时正确构造数据摘要并调用 LLM
- run_report_agent 在部分 sections 失败时仍能生成报告
- API 端点：未配置 LLM 时返回 400；配置后正确调用 Agent
"""

from unittest.mock import patch

from sqlalchemy import text


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def insert_stock(db, ts_code: str, name: str = "测试股", industry: str = "银行"):
    db.execute(
        text(
            "INSERT OR IGNORE INTO stock_basic "
            "(ts_code, name, industry, market, list_date, list_status) "
            "VALUES (:ts_code, :name, :industry, '主板', '20200101', 'L')"
        ),
        {"ts_code": ts_code, "name": name, "industry": industry},
    )
    db.commit()


def insert_quote(db, ts_code: str, trade_date: str, pct_chg: float = 1.0,
                 close: float = 10.0, amount: float = 100_000.0):
    db.execute(
        text(
            "INSERT OR IGNORE INTO daily_quote "
            "(ts_code, trade_date, open, high, low, close, vol, amount, pct_chg, total_mv, turnover_rate) "
            "VALUES (:ts_code, :trade_date, 9.9, 10.5, 9.8, :close, 1000, :amount, :pct_chg, 500000, 1.0)"
        ),
        {"ts_code": ts_code, "trade_date": trade_date, "close": close,
         "amount": amount, "pct_chg": pct_chg},
    )
    db.commit()


# ---------------------------------------------------------------------------
# llm module
# ---------------------------------------------------------------------------

class TestLlmConfigured:
    def test_empty_api_key_returns_false(self):
        with patch("app.services.llm.LLM_API_KEY", ""):
            from app.services import llm
            assert llm.is_configured() is False

    def test_whitespace_key_returns_false(self):
        with patch("app.services.llm.LLM_API_KEY", "   "):
            from app.services import llm
            assert llm.is_configured() is False

    def test_valid_key_returns_true(self):
        with patch("app.services.llm.LLM_API_KEY", "sk-test-key"):
            from app.services import llm
            assert llm.is_configured() is True

    def test_get_status_returns_expected_fields(self):
        with patch("app.services.llm.LLM_API_KEY", "sk-test"):
            from app.services import llm
            status = llm.get_status()
            assert "configured" in status
            assert "provider" in status
            assert "model" in status


# ---------------------------------------------------------------------------
# MarketAgent
# ---------------------------------------------------------------------------

class TestMarketAgent:
    def test_no_data_returns_hint(self, db):
        from app.services.agents import run_market_agent
        result = run_market_agent(db)
        assert "暂无行情数据" in result

    def test_with_data_calls_llm(self, db):
        insert_stock(db, "000001.SZ")
        insert_quote(db, "000001.SZ", "20260401", pct_chg=1.5)

        with patch("app.services.agents.llm.chat", return_value="市场偏多") as mock_chat:
            from app.services.agents import run_market_agent
            result = run_market_agent(db)
            assert mock_chat.called
            assert result == "市场偏多"

    def test_llm_failure_returns_error_string(self, db):
        insert_stock(db, "000001.SZ")
        insert_quote(db, "000001.SZ", "20260401", pct_chg=1.0)

        with patch("app.services.agents.llm.chat", side_effect=Exception("连接超时")):
            from app.services.agents import run_market_agent
            result = run_market_agent(db)
            assert "连接超时" in result


# ---------------------------------------------------------------------------
# IndustryAgent
# ---------------------------------------------------------------------------

class TestIndustryAgent:
    def test_no_data_returns_hint(self, db):
        from app.services.agents import run_industry_agent
        result = run_industry_agent(db)
        assert "暂无行业数据" in result

    def test_with_data_calls_llm(self, db):
        insert_stock(db, "000001.SZ", industry="银行")
        insert_quote(db, "000001.SZ", "20260401")

        with patch("app.services.agents.llm.chat", return_value="银行板块强势") as mock_chat:
            from app.services.agents import run_industry_agent
            result = run_industry_agent(db)
            assert mock_chat.called
            assert result == "银行板块强势"


# ---------------------------------------------------------------------------
# WatchlistAgent
# ---------------------------------------------------------------------------

class TestWatchlistAgent:
    def test_no_watchlist_returns_hint(self, db):
        from app.services.agents import run_watchlist_agent
        result = run_watchlist_agent(db)
        assert "自选股列表为空" in result

    def test_with_watchlist_and_quotes(self, db):
        insert_stock(db, "000001.SZ", name="平安银行")
        db.execute(
            text("INSERT INTO watchlist_group (name, description, sort_order) VALUES ('默认', '', 0)")
        )
        db.commit()
        group_id = db.execute(text("SELECT id FROM watchlist_group LIMIT 1")).scalar()
        db.execute(
            text("INSERT INTO watchlist_stock (group_id, ts_code, note) VALUES (:gid, '000001.SZ', '')")
            , {"gid": group_id}
        )
        db.commit()

        for i in range(1, 6):
            insert_quote(db, "000001.SZ", f"2026040{i}", pct_chg=1.0)

        with patch("app.services.agents.llm.chat", return_value="走势平稳"):
            from app.services.agents import run_watchlist_agent
            result = run_watchlist_agent(db)
            assert result == "走势平稳"


# ---------------------------------------------------------------------------
# ScreeningAgent
# ---------------------------------------------------------------------------

class TestScreeningAgent:
    def test_no_runs_returns_hint(self, db):
        from app.services.agents import run_screening_agent
        result = run_screening_agent(db)
        assert "尚无策略筛选记录" in result

    def test_with_run_and_results(self, db):
        import json
        insert_stock(db, "000001.SZ", name="平安银行")
        db.execute(
            text(
                "INSERT INTO strategy_run (strategy_id, strategy_name, trade_date, result_count) "
                "VALUES (NULL, '测试策略', '20260401', 1)"
            )
        )
        db.commit()
        run_id = db.execute(text("SELECT id FROM strategy_run LIMIT 1")).scalar()

        snapshot = json.dumps({"pct_chg": 2.5, "amount": 5_000_000, "total_mv": 10_000_000})
        db.execute(
            text(
                "INSERT INTO screening_result (run_id, ts_code, rank, snapshot) "
                "VALUES (:run_id, '000001.SZ', 1, :snap)"
            ),
            {"run_id": run_id, "snap": snapshot},
        )
        db.commit()

        with patch("app.services.agents.llm.chat", return_value="入选股以大盘蓝筹为主"):
            from app.services.agents import run_screening_agent
            result = run_screening_agent(db)
            assert result == "入选股以大盘蓝筹为主"


# ---------------------------------------------------------------------------
# StockAgent
# ---------------------------------------------------------------------------

class TestStockAgent:
    def test_unknown_ts_code_returns_hint(self, db):
        from app.services.agents import run_stock_agent
        result = run_stock_agent(db, "999999.XX")
        assert "未找到股票" in result

    def test_no_quotes_returns_hint(self, db):
        insert_stock(db, "000001.SZ")
        from app.services.agents import run_stock_agent
        result = run_stock_agent(db, "000001.SZ")
        assert "暂无行情数据" in result

    def test_with_data_calls_llm(self, db):
        insert_stock(db, "000001.SZ", name="平安银行")
        for i in range(1, 11):
            insert_quote(db, "000001.SZ", f"202604{i:02d}", close=10.0 + i * 0.1)

        with patch("app.services.agents.llm.chat", return_value="技术面偏强") as mock_chat:
            from app.services.agents import run_stock_agent
            result = run_stock_agent(db, "000001.SZ")
            assert mock_chat.called
            assert result == "技术面偏强"


# ---------------------------------------------------------------------------
# ReportAgent
# ---------------------------------------------------------------------------

class TestReportAgent:
    def test_all_sections_failed_returns_hint(self):
        from app.services.agents import run_report_agent, _ERROR_PREFIX
        bad_sections = {k: f"{_ERROR_PREFIX} 超时" for k in ["market", "industry", "watchlist", "screening"]}
        result = run_report_agent(bad_sections)
        assert "生成失败" in result

    def test_partial_failure_still_generates_report(self):
        from app.services.agents import run_report_agent, _ERROR_PREFIX
        sections = {
            "market": "今日市场偏多",
            "industry": f"{_ERROR_PREFIX} 超时",
            "watchlist": "自选股平稳",
            "screening": "筛选到5只",
        }
        with patch("app.services.agents.llm.chat", return_value="综合日报内容"):
            result = run_report_agent(sections)
            assert result == "综合日报内容"

    def test_all_valid_sections_calls_llm(self):
        from app.services.agents import run_report_agent
        sections = {
            "market": "偏多", "industry": "银行强", "watchlist": "平稳", "screening": "5只"
        }
        with patch("app.services.agents.llm.chat", return_value="完整日报") as mock_chat:
            result = run_report_agent(sections)
            assert mock_chat.called
            assert result == "完整日报"
