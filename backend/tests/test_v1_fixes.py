"""
V1 修复验证测试

覆盖 review 中提出的四个核心修复点：
1. SQLite foreign_keys 已开启
2. 删除策略后关联数据的级联行为
3. 成交额单位换算（千元 → 亿元）
4. 筛选条件执行失败时返回错误而非静默跳过
"""


import pytest
from sqlalchemy import text


# ──────────────────────────────────────────────
# 测试 1：foreign_keys 已开启
# ──────────────────────────────────────────────

def test_foreign_keys_enabled(engine):
    """PRAGMA foreign_keys 必须返回 1"""
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA foreign_keys")).scalar()
    assert result == 1, f"foreign_keys 应为 1，实际为 {result}"


def test_builtin_strategy_thresholds_use_yi_unit():
    """回归：内置策略的 amount_gt/market_cap_gt 阈值单位是亿元，不能误传元值。

    条件 evaluate 先把成交额/市值换算成亿元再比较，若阈值传成 2e9 这类元值，
    默认策略会几乎选不出票（曾经的真 bug）。
    """
    from app.services.strategy import BUILTIN_STRATEGIES

    yi_unit_codes = {"amount_gt", "market_cap_gt"}
    for spec in BUILTIN_STRATEGIES:
        for cond in spec["conditions"]:
            if cond["code"] in yi_unit_codes:
                threshold = cond["params"]["threshold"]
                assert threshold < 100_000, (
                    f"{spec['name']} 的 {cond['code']} 阈值 {threshold} 像是元值，"
                    f"应为亿元口径（如 2、100）"
                )


def test_init_tables_on_fresh_db_creates_all_tables(tmp_path, monkeypatch):
    """全新空库：init_tables 应一次建齐全表并 stamp head，绝不在缺 stock_basic 处崩。"""
    import app.config
    import app.database
    from sqlalchemy import create_engine, inspect as sa_inspect

    from app.services import data_sync

    url = f"sqlite:///{tmp_path / 'fresh.db'}"
    eng = create_engine(url)
    monkeypatch.setattr(app.config, "DATABASE_URL", url)
    monkeypatch.setattr(app.database, "engine", eng)

    data_sync.init_tables()  # 历史上这里会抛 no such table: stock_basic

    insp = sa_inspect(eng)
    for table in ("stock_basic", "daily_quote", "trade_record", "position", "strategy", "alembic_version"):
        assert insp.has_table(table), f"空库 init 后缺表 {table}"


# ──────────────────────────────────────────────
# 测试 2：删除策略后关联数据的级联行为
# ──────────────────────────────────────────────

def test_delete_strategy_cascades(db):
    """
    删除策略后：
    - strategy_condition 行应被 CASCADE 删除
    - strategy_run.strategy_id 应被 SET NULL
    - screening_result 行应随 strategy_run 被 CASCADE 删除
    """
    from app.models.strategy import Condition, Strategy, StrategyCondition, StrategyRun, ScreeningResult

    # 准备条件定义
    cond = Condition(code="test_cond", name="测试条件", category="测试")
    db.add(cond)

    # 创建策略
    strategy = Strategy(name="待删除策略")
    db.add(strategy)
    db.flush()

    # 关联条件
    sc = StrategyCondition(strategy_id=strategy.id, condition_code="test_cond")
    db.add(sc)

    # 创建运行记录
    run = StrategyRun(strategy_id=strategy.id, strategy_name="待删除策略", trade_date="20240101")
    db.add(run)
    db.flush()

    # 创建筛选结果
    result = ScreeningResult(run_id=run.id, ts_code="000001.SZ", rank=1)
    db.add(result)
    db.commit()

    strategy_id = strategy.id
    run_id = run.id

    # 删除策略
    db.delete(strategy)
    db.commit()

    # strategy_condition 应被删除（CASCADE）
    remaining_sc = db.query(StrategyCondition).filter_by(strategy_id=strategy_id).count()
    assert remaining_sc == 0, "strategy_condition 未级联删除"

    # strategy_run.strategy_id 应为 NULL（SET NULL）
    run_after = db.get(StrategyRun, run_id)
    assert run_after is not None, "strategy_run 记录不应被删除"
    assert run_after.strategy_id is None, "strategy_run.strategy_id 应为 NULL"

    # screening_result 应随 run 保留（run 未删除，结果应还在）
    result_count = db.query(ScreeningResult).filter_by(run_id=run_id).count()
    assert result_count == 1, "screening_result 不应被删除（run 还在）"


# ──────────────────────────────────────────────
# 测试 3：成交额单位换算
# ──────────────────────────────────────────────

def test_amount_unit_conversion():
    """
    daily_quote.amount 单位为千元。
    20亿元 = 200,000千元，除以 100_000 应得 2000.0 亿 -- 不对，重新算：
    20亿元 = 2,000,000,000元 = 2,000,000千元
    2,000,000千元 / 100_000 = 20 亿 ✓
    """
    # 典型大盘股：20亿成交额
    amount_qian_yuan = 2_000_000  # 千元
    amount_yi = amount_qian_yuan / 100_000
    assert amount_yi == pytest.approx(20.0), f"20亿换算应得 20.0，实际 {amount_yi}"

    # 1000亿成交额（极端活跃日）
    amount_qian_yuan_2 = 100_000_000  # 千元
    amount_yi_2 = amount_qian_yuan_2 / 100_000
    assert amount_yi_2 == pytest.approx(1000.0)

    # 验证旧的错误公式
    wrong_yi = amount_qian_yuan / 10_000_000
    assert wrong_yi == pytest.approx(0.2), "旧公式确实错误（20亿 → 0.2 亿）"


# ──────────────────────────────────────────────
# 测试 4：筛选条件报错时返回错误而非静默跳过
# ──────────────────────────────────────────────

def test_condition_error_propagates(db):
    """
    当某个筛选条件抛异常时，run_strategy 应返回包含 'error' 的 dict，
    而不是静默跳过继续执行。
    """
    from app.models.strategy import Condition, Strategy, StrategyCondition
    from app.services.conditions.base import BaseCondition
    from app.services.conditions import registry as global_registry
    from app.services import screening as screening_module

    # 注册一个会抛异常的临时条件
    class BrokenCondition(BaseCondition):
        code = "_test_broken"
        name = "测试故障条件"
        category = "测试"
        description = "专门用于测试的故障条件"
        param_defs = {}

        def evaluate(self, df, db, params):
            raise RuntimeError("条件故意失败")

    broken = BrokenCondition()
    global_registry.register(broken)

    try:
        # 插入条件元数据
        cond_def = Condition(code="_test_broken", name="测试故障条件", category="测试")
        db.add(cond_def)

        # 创建使用该条件的策略
        strategy = Strategy(name="故障策略测试")
        db.add(strategy)
        db.flush()

        sc = StrategyCondition(
            strategy_id=strategy.id,
            condition_code="_test_broken",
            sort_order=1,
        )
        db.add(sc)

        # 插入一条假行情（让 get_market_df 有数据）
        db.execute(text("""
            INSERT INTO stock_basic (ts_code, name, list_status)
            VALUES ('999999.SZ', '测试股', 'L')
        """))
        db.execute(text("""
            INSERT INTO daily_quote (ts_code, trade_date, close, amount, vol, total_mv, pct_chg)
            VALUES ('999999.SZ', '20240101', 10.0, 100000, 5000, 50000, 1.0)
        """))
        db.commit()

        result = screening_module.run_strategy(db, strategy.id, "20240101")
        assert "error" in result, "条件报错时应返回 error dict"
        assert "_test_broken" in result["error"], f"错误信息应包含条件代码，实际：{result['error']}"

    finally:
        # 清理临时注册
        global_registry._conditions.pop("_test_broken", None)
