# Market Sentiment Upgrade Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 `stock-assistant` 增加可回填、可视化、可被 AI 和页面复用的市场情绪能力，覆盖连板高度、炸板率、昨日涨停溢价、高位股晋级率、主线持续天数。

**Architecture:** 按“原始数据 -> 情绪快照 -> API -> 首页/情绪页 -> AI/页面软联动”五阶段推进。每阶段保持最小闭环：先补测试，再实现，再跑针对性验证，再做人工验收与 Git 检查点；任一阶段未通过，不得进入下一阶段。

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy 2.0, Alembic, SQLite, Vue 3, TypeScript, Pinia, Element Plus, ECharts, uv, pytest, pnpm

---

## 执行总规则

1. 只按阶段执行，不允许跨阶段偷跑。
2. 每个阶段都必须完成：
   - 红绿测试
   - 数据抽样校验
   - 人工验收
   - Git 检查点
3. 若当前阶段任一验收项未通过，禁止进入下一阶段。
4. 所有提交使用中文、简洁、Conventional Commits 风格。
5. 每完成一个阶段就停下汇报，不继续做下一阶段，等待用户确认。
6. 当前按用户 6000 积分权限执行，Phase 1 仅允许依赖 `5000/6000` 权限接口；`theme_heat_daily` 固定使用 `ths_hot(market="概念板块", is_new="N")`，禁止依赖 `limit_cpt_list` 等 8000+ 接口。

---

## Phase 1: 情绪原始数据底座

### Task 1: 新建原始数据模型测试

**Files:**
- Create: `backend/tests/test_market_sentiment_models.py`
- Reference: `backend/app/models/top_list.py`
- Reference: `backend/tests/test_v8_models.py`

**Step 1: 写失败测试**

新增测试覆盖：
- `limit_event_daily` 能建表
- `theme_heat_daily` 能建表
- 主键/索引存在

测试示例：

```python
def test_limit_event_daily_table_created(test_engine):
    inspector = inspect(test_engine)
    assert "limit_event_daily" in inspector.get_table_names()
```

**Step 2: 跑失败**

Run: `cd backend && uv run pytest tests/test_market_sentiment_models.py -v`
Expected: FAIL，提示表不存在或模型未导出。

**Step 3: 最小实现**

创建：
- `backend/app/models/limit_event.py`
- `backend/app/models/theme_heat.py`

修改：
- `backend/app/models/__init__.py`

**Step 4: 跑通过**

Run: `cd backend && uv run pytest tests/test_market_sentiment_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/models/limit_event.py backend/app/models/theme_heat.py backend/app/models/__init__.py backend/tests/test_market_sentiment_models.py
git commit -m "feat: 新增情绪原始数据模型"
```

### Task 2: 新建迁移测试与迁移文件

**Files:**
- Create: `backend/tests/test_market_sentiment_migration.py`
- Create: `backend/alembic/versions/<timestamp>_market_sentiment_raw_tables.py`

**Step 1: 写失败测试**

覆盖：
- Alembic 升级后出现 `limit_event_daily` / `theme_heat_daily`
- 只有一个 `head`

**Step 2: 跑失败**

Run: `cd backend && uv run pytest tests/test_market_sentiment_migration.py -v`
Expected: FAIL，提示 migration 缺失。

**Step 3: 实现迁移**

迁移内容：
- 新建 `limit_event_daily`
- 新建 `theme_heat_daily`
- 补索引
- 完整 downgrade

**Step 4: 跑通过**

Run: `cd backend && uv run pytest tests/test_market_sentiment_migration.py -v`
Run: `cd backend && uv run alembic heads`
Expected: 测试 PASS，且仅有一个 head。

**Step 5: Commit**

```bash
git add backend/alembic/versions/*.py backend/tests/test_market_sentiment_migration.py
git commit -m "feat: 新增情绪原始表迁移"
```

### Task 3: 补原始同步测试

**Files:**
- Create: `backend/tests/test_market_sentiment_sync.py`
- Reference: `backend/tests/test_v8_sync.py`

**Step 1: 写失败测试**

覆盖：
- `sync_limit_event_daily()` 空结果不报错
- `sync_limit_event_daily()` 先删后插
- `sync_theme_heat_daily()` 返回统计值
- 同步时显式使用 `TUSHARE_TOKEN`
- `sync_theme_heat_daily()` 使用 `ths_hot(market="概念板块")`

**Step 2: 跑失败**

Run: `cd backend && uv run pytest tests/test_market_sentiment_sync.py -v`
Expected: FAIL，提示同步函数不存在。

**Step 3: 最小实现**

创建：
- `backend/app/services/sync_limit_event.py`
- `backend/app/services/sync_theme_heat.py`

实现要求：
- 增量按交易日同步
- 支持空数据安全返回
- 支持同日重跑覆盖
- `theme_heat_daily` 固定改用 `ths_hot(market="概念板块", is_new="N")`
- 同一交易日若有多条热榜快照，按 `rank_time` 去重后落库

**Step 4: 跑通过**

Run: `cd backend && uv run pytest tests/test_market_sentiment_sync.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/sync_limit_event.py backend/app/services/sync_theme_heat.py backend/tests/test_market_sentiment_sync.py
git commit -m "feat: 新增情绪原始数据同步"
```

### Task 4: 接入每日同步与历史回填

**Files:**
- Modify: `backend/app/services/data_sync.py`
- Modify: `backend/app/services/backfill.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_market_sentiment_sync.py`

**Step 1: 写失败测试**

新增覆盖：
- `sync_daily()` 会调用情绪原始同步
- `backfill_all()` 会回填情绪原始数据
- 与现有 `sync_lock` 兼容，不并发冲突

**Step 2: 跑失败**

Run: `cd backend && uv run pytest tests/test_market_sentiment_sync.py -v -k "daily or backfill or lock"`
Expected: FAIL

**Step 3: 最小实现**

要求：
- 日增量放在行情同步之后
- 历史回填放在 `daily_quote` 完成后
- 保留阶段日志

**Step 4: 跑通过**

Run: `cd backend && uv run pytest tests/test_market_sentiment_sync.py -v -k "daily or backfill or lock"`
Expected: PASS

**Step 5: 数据抽样校验**

Run:
- 手动触发一次小范围同步
- 任选 3 个交易日，核对 `limit_list_d` 与库里原始行数
- 任选 3 个交易日，核对 `ths_hot(market="概念板块", is_new="N")` 去重后与库里原始行数

说明：
- `ths_hot` 同一交易日可能返回多次快照；Phase 1 固定按 `trade_date + ts_code` 去重，优先保留最新 `rank_time`，若时间相同则保留 `hot` 更高记录

Expected:
- 行数可解释
- 无重复、无空主键

### Task 5: Phase 1 Gate

**Files:**
- Verify: `backend/tests/`
- Verify: `git status --short`

**Step 1: 跑阶段回归**

Run:
- `cd backend && uv run pytest tests/test_market_sentiment_models.py -v`
- `cd backend && uv run pytest tests/test_market_sentiment_migration.py -v`
- `cd backend && uv run pytest tests/test_market_sentiment_sync.py -v`

Expected: 全部 PASS

**Step 2: 手工验收**

验收动作：
- 触发同步
- 触发回填
- 观察日志
- 核对至少 10 个样本

Expected:
- 原始表有数据
- 锁与状态正常

**Step 3: Commit**

```bash
git add backend/app/services/data_sync.py backend/app/services/backfill.py backend/app/main.py
git commit -m "feat: 接入情绪原始数据增量与回填"
```

**Step 4: 停止条件**

若本任务任一项未通过，禁止进入 Phase 2。

---

## Phase 2: 情绪快照计算与 API

### Task 6: 新建情绪快照模型与测试

**Files:**
- Modify: `backend/tests/test_market_sentiment_models.py`
- Create: `backend/app/models/market_sentiment.py`
- Modify: `backend/app/models/__init__.py`

**Step 1: 写失败测试**

覆盖：
- `market_sentiment_daily` 建表
- 关键字段存在
- `trade_date` 唯一

**Step 2: 跑失败**

Run: `cd backend && uv run pytest tests/test_market_sentiment_models.py -v -k "sentiment"`
Expected: FAIL

**Step 3: 最小实现**

新增模型：
- `backend/app/models/market_sentiment.py`

新增迁移：
- 扩展 market sentiment migration

**Step 4: 跑通过**

Run: `cd backend && uv run pytest tests/test_market_sentiment_models.py -v -k "sentiment"`
Expected: PASS

### Task 7: 写 5 指标服务测试

**Files:**
- Create: `backend/tests/test_market_sentiment_service.py`
- Create: `backend/app/services/market_sentiment.py`

**Step 1: 写失败测试**

覆盖以下函数：
- `calculate_max_limit_height`
- `calculate_broken_rate`
- `calculate_yday_limit_premium`
- `calculate_high_board_promotion_rate`
- `calculate_main_theme_streak`

测试要求：
- 用最小样本数据构造清晰断言
- 至少覆盖 1 个空数据边界

示例：

```python
def test_calculate_broken_rate():
    result = calculate_broken_rate(limit_up_count=10, limit_broken_count=5)
    assert result == 5 / 15
```

**Step 2: 跑失败**

Run: `cd backend && uv run pytest tests/test_market_sentiment_service.py -v`
Expected: FAIL

**Step 3: 最小实现**

在 `backend/app/services/market_sentiment.py` 中实现：
- 纯函数计算
- 查询装配函数
- 快照落库函数

**Step 4: 跑通过**

Run: `cd backend && uv run pytest tests/test_market_sentiment_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/models/market_sentiment.py backend/app/services/market_sentiment.py backend/tests/test_market_sentiment_service.py backend/tests/test_market_sentiment_models.py
git commit -m "feat: 新增市场情绪快照计算"
```

### Task 8: 接入快照生成与历史重算

**Files:**
- Modify: `backend/app/services/data_sync.py`
- Modify: `backend/app/services/backfill.py`
- Test: `backend/tests/test_market_sentiment_sync.py`

**Step 1: 写失败测试**

覆盖：
- 日增量同步后生成当日快照
- 历史回填后能批量重算快照

**Step 2: 跑失败**

Run: `cd backend && uv run pytest tests/test_market_sentiment_sync.py -v -k "snapshot"`
Expected: FAIL

**Step 3: 最小实现**

要求：
- 情绪快照生成放在原始情绪同步之后
- 回填时按交易日顺序重算

**Step 4: 跑通过**

Run: `cd backend && uv run pytest tests/test_market_sentiment_sync.py -v -k "snapshot"`
Expected: PASS

### Task 9: 新建情绪 API 与测试

**Files:**
- Create: `backend/app/api/sentiment.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_market_sentiment_api.py`

**Step 1: 写失败测试**

覆盖接口：
- `GET /api/dashboard/sentiment/summary`
- `GET /api/dashboard/sentiment/history`
- `GET /api/dashboard/sentiment/themes`
- `GET /api/dashboard/sentiment/detail/{trade_date}`

**Step 2: 跑失败**

Run: `cd backend && uv run pytest tests/test_market_sentiment_api.py -v`
Expected: FAIL

**Step 3: 最小实现**

要求：
- 路由职责单一
- 服务层统一返回结构化数据
- 无数据时返回空结构而非 500

**Step 4: 跑通过**

Run: `cd backend && uv run pytest tests/test_market_sentiment_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/api/sentiment.py backend/app/main.py backend/tests/test_market_sentiment_api.py backend/app/services/data_sync.py backend/app/services/backfill.py
git commit -m "feat: 新增市场情绪接口"
```

### Task 10: Phase 2 Gate

**Step 1: 跑阶段回归**

Run:
- `cd backend && uv run pytest tests/test_market_sentiment_service.py -v`
- `cd backend && uv run pytest tests/test_market_sentiment_api.py -v`
- `cd backend && uv run pytest tests/test_market_sentiment_sync.py -v`

Expected: 全部 PASS

**Step 2: 数据抽样校验**

抽样要求：
- 选择 1 个极热日
- 选择 1 个极冷日
- 选择 1 个普通震荡日

核对：
- 最高板
- 炸板率
- 昨日涨停溢价
- 高位晋级率
- 主线主题

Expected:
- 指标值可解释
- 公式与样本一致

**Step 3: 停止条件**

若本任务任一项未通过，禁止进入 Phase 3。

---

## Phase 3: 首页摘要与独立情绪页

### Task 11: 新增前端类型、API 和 store

**Files:**
- Modify: `frontend/src/api/index.ts`
- Create: `frontend/src/types/sentiment.ts`
- Create: `frontend/src/stores/sentiment.ts`

**Step 1: 先补类型**

定义：
- `SentimentSummary`
- `SentimentHistoryPoint`
- `MainThemeHistoryPoint`
- `SentimentDetail`

**Step 2: 实现 API 封装**

新增：
- `getSentimentSummary`
- `getSentimentHistory`
- `getSentimentThemes`
- `getSentimentDetail`

**Step 3: 实现 store**

要求：
- 独立维护 `summary/history/themes/detail`
- 提供 `fetchSummary()` / `fetchPageData()`

**Step 4: 验证**

Run:
- `cd frontend && pnpm type-check`

Expected: PASS

### Task 12: 首页增加情绪摘要卡片

**Files:**
- Modify: `frontend/src/views/DashboardView.vue`
- Modify: `frontend/src/stores/dashboard.ts`
- Modify: `frontend/src/types/dashboard.ts`

**Step 1: 最小实现**

首页只增加：
- 连板高度
- 炸板率
- 昨日涨停溢价
- 高位晋级率
- 主线主题

要求：
- 不加历史大图
- 不挤压现有概览区

**Step 2: 验证**

Run:
- `cd frontend && pnpm type-check`
- `cd frontend && pnpm build`

Expected: PASS

### Task 13: 新增独立情绪页

**Files:**
- Create: `frontend/src/views/SentimentView.vue`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/components/AppSidebar.vue`

**Step 1: 页面最小骨架**

包含：
- 顶部摘要卡片
- 5 指标走势图
- 主线演化图
- 分项解释区域

**Step 2: 图表实现**

使用 ECharts：
- 折线图展示 5 指标
- 时间轴或折线展示主线持续天数

**Step 3: 路由接入**

新增路由：
- `/sentiment`

导航增加：
- “市场情绪”

**Step 4: 验证**

Run:
- `cd frontend && pnpm type-check`
- `cd frontend && pnpm build`

Expected: PASS

### Task 14: Phase 3 Gate

**Step 1: 浏览器手工验收**

验收动作：
- 打开首页，确认摘要卡片显示
- 打开 `/sentiment`
- 切换不同历史天数
- 检查空数据状态
- 检查主线演化展示

Expected:
- 无白屏
- 无空图
- 无明显错位
- 数值与 API 一致

**Step 2: Commit**

```bash
git add frontend/src/api/index.ts frontend/src/types/sentiment.ts frontend/src/stores/sentiment.ts frontend/src/views/SentimentView.vue frontend/src/router/index.ts frontend/src/components/AppSidebar.vue frontend/src/views/DashboardView.vue frontend/src/stores/dashboard.ts frontend/src/types/dashboard.ts
git commit -m "feat: 新增市场情绪页与首页摘要"
```

**Step 3: 停止条件**

若本任务任一项未通过，禁止进入 Phase 4。

---

## Phase 4: AI 软联动

### Task 15: 扩展日报 Agent 测试与实现

**Files:**
- Modify: `backend/tests/test_v4_analysis.py`
- Modify: `backend/app/services/agents/daily.py`
- Create: `backend/app/services/sentiment_summary.py`

**Step 1: 写失败测试**

覆盖：
- 市场 Agent 能读取情绪快照
- 无情绪数据时降级为原逻辑

**Step 2: 跑失败**

Run: `cd backend && uv run pytest tests/test_v4_analysis.py -v -k "sentiment"`
Expected: FAIL

**Step 3: 最小实现**

要求：
- 增加情绪摘要拼接
- 明确“不预测涨跌，只解释环境”

**Step 4: 跑通过**

Run: `cd backend && uv run pytest tests/test_v4_analysis.py -v -k "sentiment"`
Expected: PASS

### Task 16: 扩展交易计划 Agent 测试与实现

**Files:**
- Modify: `backend/tests/test_v5_plan.py`
- Modify: `backend/app/services/agents/plan.py`

**Step 1: 写失败测试**

覆盖：
- 计划 Agent 在情绪偏冷时输出风险提示
- 无情绪数据时仍可生成计划

**Step 2: 跑失败**

Run: `cd backend && uv run pytest tests/test_v5_plan.py -v -k "sentiment"`
Expected: FAIL

**Step 3: 最小实现**

要求：
- 只补充市场情绪背景
- 不改三套方案主结构

**Step 4: 跑通过**

Run: `cd backend && uv run pytest tests/test_v5_plan.py -v -k "sentiment"`
Expected: PASS

### Task 17: Phase 4 Gate

**Step 1: AI 降级回归**

Run:
- `cd backend && uv run pytest tests/test_v4_analysis.py -v`
- `cd backend && uv run pytest tests/test_v5_plan.py -v`

Expected: PASS

**Step 2: 手工验收**

验收动作：
- 关闭 LLM 配置验证降级
- 打开 LLM 配置验证情绪摘要进入日报/计划

Expected:
- 无配置时不报 500
- 有配置时能引用情绪指标

**Step 3: Commit**

```bash
git add backend/app/services/agents/daily.py backend/app/services/agents/plan.py backend/app/services/sentiment_summary.py backend/tests/test_v4_analysis.py backend/tests/test_v5_plan.py
git commit -m "feat: 接入情绪摘要到日报与交易计划"
```

**Step 4: 停止条件**

若本任务任一项未通过，禁止进入 Phase 5。

---

## Phase 5: 页面软联动与总回归

### Task 18: 筛选页与分析页接入情绪提示

**Files:**
- Modify: `frontend/src/views/ScreeningView.vue`
- Modify: `frontend/src/views/AnalysisView.vue`
- Modify: `frontend/src/views/PlanGenerateView.vue`
- Modify: `frontend/src/stores/screening.ts`
- Modify: `frontend/src/stores/analysis.ts`
- Modify: `frontend/src/stores/planGenerate.ts`

**Step 1: 最小实现**

只增加提示区：
- 当前情绪摘要
- 主线主题
- 风险偏好提示

不增加硬筛选条件，不增加额外图表。

**Step 2: 验证**

Run:
- `cd frontend && pnpm type-check`
- `cd frontend && pnpm build`

Expected: PASS

### Task 19: 文档收口与全链路回归

**Files:**
- Modify: `docs/README.md`
- Modify: `CLAUDE.md`
- Create: `docs/market-sentiment-acceptance.md`

**Step 1: 更新文档**

补充：
- 新增情绪模块入口
- 新 API
- 同步与回填说明
- 验收步骤

**Step 2: 后端全量回归**

Run: `cd backend && uv run pytest tests/ -v`
Expected: PASS

**Step 3: 前端全量回归**

Run:
- `cd frontend && pnpm type-check`
- `cd frontend && pnpm build`

Expected: PASS

**Step 4: 手工全链路验收**

动作：
- 同步/回填
- 首页
- 情绪页
- AI 日报
- 计划生成
- 筛选页提示

Expected:
- 全链路可走通
- 无假成功、无明显数据错位

### Task 20: Final Gate

**Step 1: Git 检查**

Run: `git status --short`
Expected: 仅剩可解释文档或收尾变更。

**Step 2: Commit**

```bash
git add frontend/src/views/ScreeningView.vue frontend/src/views/AnalysisView.vue frontend/src/views/PlanGenerateView.vue frontend/src/stores/screening.ts frontend/src/stores/analysis.ts frontend/src/stores/planGenerate.ts docs/README.md CLAUDE.md docs/market-sentiment-acceptance.md
git commit -m "feat: 完成市场情绪软联动与全链回归"
```

**Step 3: 停止条件**

若本任务任一项未通过，本次升级不得宣告完成。

---

Plan complete and saved to `docs/plans/2026-04-08-market-sentiment-upgrade.md`. Two execution options:

1. Subagent-Driven (this session) - I dispatch fresh subagent per task, review between tasks, fast iteration
2. Parallel Session (separate) - Open new session with executing-plans, batch execution with checkpoints

Which approach?
