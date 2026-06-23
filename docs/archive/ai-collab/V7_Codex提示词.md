# V7 Codex 执行提示词

本文件包含交给 Codex 的分阶段提示词。每个提示词设计为一个独立子代理任务。
Codex 应默认使用子代理模式执行，Phase 内标记为"可并行"的任务可同时启动。

> **使用方式**：把每个 `### Prompt` 块的内容直接粘贴给 Codex 作为任务描述。

---

## Phase A：准备工作（2 个并行任务）

> Phase A 的两个任务互相独立，可同时启动。完成后运行 `cd backend && uv run pytest tests/ -v` 验证无回归。

---

### Prompt A1：修复 position.py 变量命名

```
你在 stock-assistant 项目中工作。请修复一个变量命名问题：

文件：`backend/app/services/position.py`，函数 `get_position_summary()`

当前第 178 行：
```python
total_realized_pnl = db.query(Position).all()
```

这个变量名有误导性 —— 它查询的是所有 Position 对象，不是一个数值。

修复步骤：
1. 将变量名 `total_realized_pnl` 改为 `all_positions`
2. 同步更新第 187 行的引用：
   ```python
   "total_realized_pnl": round_money(sum(p.realized_pnl for p in all_positions)),
   ```

验证：`cd backend && uv run pytest tests/ -v` 全部通过，功能行为完全不变。
```

---

### Prompt A2：创建 V7 开发分支 + 版本号准备

```
你在 stock-assistant 项目中工作。请完成版本管理准备：

1. 确认当前在 `codex/v6` 分支且工作区干净
2. 如果 `v6.0` 标签不存在，打标签：`git tag v6.0`
3. 创建新分支：`git checkout -b codex/v7`
4. 更新后端版本号：在 `backend/app/main.py` 中找到 health 端点的 version 字段，改为 `"7.0.0"`
5. 更新 `CLAUDE.md` 中的"当前主开发版本"改为 V7，"当前建议开发分支"改为 `codex/v7`
6. 提交：`git commit -m "chore: V7 版本管理准备"`

注意：
- 不要改其他文件
- 不要推送到远程
```

---

## Phase B：后端核心功能（顺序执行）

> Phase B 依赖 Phase A 完成。B1 → B2 → B3 → B4 严格顺序执行。

---

### Prompt B1：数据模型

```
你在 stock-assistant 项目中工作，正在开发 V7（复盘 + 行为模式识别）。

请先阅读 `docs/V7_架构设计与开发计划.md` 的第 2 节了解数据模型设计，以及 `CLAUDE.md` 了解项目规则。

### 任务：创建复盘和行为模式数据模型

1. 新建 `backend/app/models/review.py`，定义两个模型：

**TradeReview**：
- id: Integer, PK, autoincrement
- ts_code: String(20), not null, index
- stock_name: String(50), not null
- plan_id: Integer, FK → trading_plan.id (ondelete SET NULL), nullable
- total_buy_amount: Float, not null
- total_sell_amount: Float, not null
- total_fee: Float, not null
- realized_pnl: Float, not null
- trade_count: Integer, not null
- first_trade_date: String(10), not null
- last_trade_date: String(10), not null
- holding_days: Integer, not null
- scores: Text, not null (JSON: 8 维度评分)
- overall_score: Float, not null
- analysis: Text, not null (Markdown)
- improvement: Text, nullable (Markdown)
- user_notes: Text, nullable
- created_at: String(30), not null
- updated_at: String(30), not null

索引：ix_review_ts_code on ts_code，ix_review_plan_id on plan_id

**BehaviorPattern**：
- id: Integer, PK, autoincrement
- pattern_type: String(20), not null ("strength" / "weakness")
- title: String(100), not null
- description: Text, not null
- dimension: String(30), nullable
- evidence_ids: Text, nullable (JSON 数组)
- status: String(20), not null, default "active" ("active" / "resolved" / "dismissed")
- created_at: String(30), not null
- updated_at: String(30), not null

2. 在 `backend/app/models/__init__.py` 中导入并导出 TradeReview 和 BehaviorPattern。

验证：`cd backend && uv run pytest tests/ -v` 全部通过（新模型的表应通过 create_all 自动创建）。
```

---

### Prompt B2：复盘服务层 + 校验契约

```
你在 stock-assistant 项目中工作，正在开发 V7。

请先阅读 `docs/V7_架构设计与开发计划.md` 的第 2-3 节。

### 任务 1：创建 review_contract.py

新建 `backend/app/services/review_contract.py`，定义：

REVIEW_DIMENSIONS：8 个维度的键名列表
```python
REVIEW_DIMENSIONS = [
    "entry_timing", "exit_timing", "stop_loss", "take_profit",
    "position_sizing", "holding_period", "discipline", "risk_reward",
]
```

DIMENSION_LABELS：键名到中文名的映射 dict

validate_scores(scores: dict) -> tuple[dict | None, str | None]：
- 检查 scores 是否包含全部 8 个键
- 每个分数必须是 1-10 的整数
- 返回 (normalized_scores, None) 或 (None, error_message)

calculate_overall_score(scores: dict) -> float：
- 8 个维度的算术平均，round 到 1 位小数

format_review(review: TradeReview) -> dict：
- 序列化为 API 响应格式
- scores 字段从 JSON 字符串解析为 dict
- 包含所有字段

format_pattern(pattern: BehaviorPattern) -> dict：
- 序列化为 API 响应格式
- evidence_ids 从 JSON 解析为 list

### 任务 2：创建 review.py 服务

新建 `backend/app/services/review.py`，定义：

build_review_context(db, ts_code) -> dict | None：
- 查询该股所有 TradeRecord（按时间升序）
- 查询该股 Position
- 查询关联的 TradingPlan（取 plan_id 出现最多的那个，或最近的 executed 计划）
- 查询持仓期间的 DailyQuote（首笔交易日前 10 天 → 末笔交易日后 20 天）
- 读取 total_capital 配置
- 如果没有交易记录，返回 None
- 返回包含所有上下文的 dict

create_review(db, ts_code, llm_result: dict) -> dict | error：
- 用 review_contract 验证 scores
- 从 build_review_context 获取交易摘要数据
- 创建 TradeReview 记录
- 返回 format_review(review)

list_reviews(db, ts_code=None) -> dict：
- 按 created_at 降序
- 可选按 ts_code 筛选
- 返回 {"reviews": [...]}

get_review_detail(db, review_id) -> dict | None：
- 返回单条复盘详情

update_review_notes(db, review_id, notes: str) -> dict | error：
- 更新 user_notes 字段

delete_review(db, review_id) -> dict | error：
- 删除复盘记录

get_review_stats(db) -> dict：
- 纯数值计算，不调 LLM
- 返回：total_reviews, avg_overall_score, avg_scores (各维度平均), best_dimension, worst_dimension, win_count, loss_count, total_reviewed_pnl

### 任务 3：创建 pattern.py 服务

新建 `backend/app/services/pattern.py`，定义：

list_patterns(db, status=None) -> dict：
- 按 updated_at 降序
- 可选按 status 筛选
- 返回 {"patterns": [...]}

save_patterns(db, patterns_data: list[dict]) -> dict：
- 将所有 status="active" 的旧模式标记为被替换（直接删除）
- 插入新模式
- 返回 {"patterns": [...]}

update_pattern_status(db, pattern_id, status: str) -> dict | error：
- status 必须是 "active" / "resolved" / "dismissed"
- 更新并返回

验证：`cd backend && uv run pytest tests/ -v` 全部通过。
```

---

### Prompt B3：复盘 LLM Agent

```
你在 stock-assistant 项目中工作，正在开发 V7。

请先阅读 `docs/V7_架构设计与开发计划.md` 的第 3.2、3.3、6 节了解 LLM Prompt 设计。
同时阅读 `backend/app/services/agents/plan.py` 了解现有 Agent 的代码模式。

### 任务：创建复盘 LLM Agent

新建 `backend/app/services/agents/review.py`，定义：

_REVIEW_SYSTEM_PROMPT：复盘 Agent 的 system prompt
- "你是一个 A 股交易复盘助手。根据提供的交易数据进行专业复盘分析。严格按要求的 JSON 格式输出。"

run_review_agent(db, ts_code) -> dict：
- 调用 review.build_review_context(db, ts_code) 获取上下文
- 如果上下文为空，返回 build_error("该股票无交易记录")
- 构建 prompt（参考设计文档第 6.1 节的模板）：
  - 股票信息
  - 交易计划（如有）：方向、目标价、止损价、止盈梯度、仓位比例
  - 交易记录时间线：日期、方向、价格、数量、金额、费用
  - 持仓期间行情走势：开盘/收盘/最高/最低/成交额的关键节点
- 调用 _safe_llm_call(prompt, max_tokens=2000, system_prompt=_REVIEW_SYSTEM_PROMPT)
- 用 _extract_first_json_payload 提取 JSON
- 用 review_contract.validate_scores 校验
- 返回 {"status": "ok", "scores": ..., "analysis": ..., "improvement": ...}
- 如果 LLM 返回格式异常，返回 build_error 说明

run_pattern_agent(db) -> dict：
- 查询所有 TradeReview
- 如果不足 3 条，返回 build_error("复盘数据不足 3 条，无法分析行为模式")
- 计算各维度平均分、标准差
- 统计盈利/亏损笔数
- 构建 prompt（参考设计文档第 6.2 节的模板）
- 调用 _safe_llm_call(prompt, max_tokens=1500, system_prompt=_REVIEW_SYSTEM_PROMPT)
- 用 _extract_first_json_payload 提取 JSON 数组
- 校验每个 pattern 有 pattern_type, title, description 字段
- 返回 {"status": "ok", "patterns": [...]}

在 `backend/app/services/agents/__init__.py` 中导出：
```python
from app.services.agents.review import run_review_agent, run_pattern_agent
```

验证：`cd backend && uv run pytest tests/ -v` 全部通过。
```

---

### Prompt B4：API 路由 + 测试

```
你在 stock-assistant 项目中工作，正在开发 V7。

请先阅读 `docs/V7_架构设计与开发计划.md` 的第 3.1 节了解 API 设计。
同时阅读 `backend/app/api/trade.py` 了解现有 API 的代码模式（Pydantic 模型、错误处理）。

### 任务 1：API 路由

新建 `backend/app/api/review.py`，定义以下路由：

```python
router = APIRouter(prefix="/review", tags=["review"])
```

路由列表：
- POST /generate/{ts_code} — 调用 run_review_agent → review.create_review → 返回 201
- GET / — 调用 review.list_reviews(?ts_code) → 返回 200
- GET /stats — 调用 review.get_review_stats → 返回 200
- GET /patterns — 调用 pattern.list_patterns(?status) → 返回 200
- POST /patterns/refresh — 调用 run_pattern_agent → pattern.save_patterns → 返回 200
- GET /{review_id} — 调用 review.get_review_detail → 返回 200 或 404
- PUT /{review_id}/notes — 调用 review.update_review_notes → 返回 200
- DELETE /{review_id} — 调用 review.delete_review → 返回 200
- PATCH /patterns/{pattern_id}/status — 调用 pattern.update_pattern_status → 返回 200

Pydantic 输入模型：
- NotesUpdate: { notes: str }
- PatternStatusUpdate: { status: Literal["active", "resolved", "dismissed"] }

注意：/stats 和 /patterns 路由必须放在 /{review_id} 之前，否则会被路径参数捕获。

错误处理使用 `app/errors.py` 中的 `raise_service_error()`。

在 `backend/app/main.py` 中注册路由：
```python
from app.api import review
app.include_router(review.router, prefix="/api")
```

### 任务 2：测试

新建 `backend/tests/test_v7_review.py`，覆盖以下场景：

复盘服务测试：
- build_review_context：有交易记录 → 返回上下文 dict
- build_review_context：无交易记录 → 返回 None
- create_review：合法 scores → 创建成功
- create_review：分数超范围 → 返回错误
- create_review：缺少维度 → 返回错误
- list_reviews：返回列表，按时间降序
- list_reviews：按 ts_code 筛选
- get_review_detail：存在 → 返回详情
- get_review_detail：不存在 → 返回 None
- update_review_notes：更新成功
- delete_review：删除成功
- delete_review：不存在 → 返回错误
- get_review_stats：正确计算平均分和维度排名

模式服务测试：
- save_patterns：保存成功，旧 active 模式被清除
- list_patterns：按 status 筛选
- update_pattern_status：合法状态 → 更新成功
- update_pattern_status：非法状态 → 返回错误

新建 `backend/tests/test_v7_review_api.py`，覆盖：
- POST /api/review/generate/{ts_code} — 需先创建交易记录（mock LLM 调用）
- GET /api/review — 列表
- GET /api/review/{id} — 详情
- PUT /api/review/{id}/notes — 更新反思
- DELETE /api/review/{id} — 删除
- GET /api/review/stats — 统计
- PATCH /api/review/patterns/{id}/status — 更新模式状态

对于 LLM 调用，使用 monkeypatch/mock 替换 `app.services.agents.review.run_review_agent` 和 `run_pattern_agent`，返回固定结果。参考 `backend/tests/test_v5_plan.py` 中的 mock 模式。

运行 `cd backend && uv run pytest tests/ -v` 确保全部通过（包括 V1-V6 旧测试）。
```

---

## Phase C：前端功能（顺序执行）

> Phase C 依赖 Phase B 完成。C1 → C2 严格顺序执行。

---

### Prompt C1：前端类型 + API + Store

```
你在 stock-assistant 项目中工作，正在开发 V7 前端。

请先阅读 `docs/V7_架构设计与开发计划.md` 第 4 节了解前端设计，以及 `CLAUDE.md` 了解前端规范。
同时阅读 `frontend/src/types/trade.ts` 和 `frontend/src/types/position.ts` 了解类型定义模式。

### 步骤 1：类型定义

新建 `frontend/src/types/review.ts`：

```typescript
export interface ReviewScores {
  entry_timing: number
  exit_timing: number
  stop_loss: number
  take_profit: number
  position_sizing: number
  holding_period: number
  discipline: number
  risk_reward: number
}

export interface TradeReview {
  id: number
  ts_code: string
  stock_name: string
  plan_id: number | null
  total_buy_amount: number
  total_sell_amount: number
  total_fee: number
  realized_pnl: number
  trade_count: number
  first_trade_date: string
  last_trade_date: string
  holding_days: number
  scores: ReviewScores
  overall_score: number
  analysis: string
  improvement: string | null
  user_notes: string | null
  created_at: string
  updated_at: string
}

export interface ReviewStats {
  total_reviews: number
  avg_overall_score: number
  avg_scores: ReviewScores
  best_dimension: string
  worst_dimension: string
  win_count: number
  loss_count: number
  total_reviewed_pnl: number
}

export type PatternType = 'strength' | 'weakness'
export type PatternStatus = 'active' | 'resolved' | 'dismissed'

export interface BehaviorPattern {
  id: number
  pattern_type: PatternType
  title: string
  description: string
  dimension: string | null
  evidence_ids: number[]
  status: PatternStatus
  created_at: string
  updated_at: string
}
```

### 步骤 2：API 封装

在 `frontend/src/api/index.ts` 中新增：

```typescript
import type { TradeReview, ReviewStats, BehaviorPattern } from '@/types/review'

// ---- 交易复盘 (V7) ----
export const generateReview = (tsCode: string) =>
  http.post<TradeReview>(`/api/review/generate/${tsCode}`, null, { timeout: 120_000 })
export const listReviews = (tsCode?: string) =>
  http.get<{ reviews: TradeReview[] }>('/api/review', { params: tsCode ? { ts_code: tsCode } : {} })
export const getReview = (id: number) => http.get<TradeReview>(`/api/review/${id}`)
export const updateReviewNotes = (id: number, notes: string) =>
  http.put<TradeReview>(`/api/review/${id}/notes`, { notes })
export const deleteReview = (id: number) => http.delete(`/api/review/${id}`)
export const getReviewStats = () => http.get<ReviewStats>('/api/review/stats')

// ---- 行为模式 (V7) ----
export const listPatterns = (status?: string) =>
  http.get<{ patterns: BehaviorPattern[] }>('/api/review/patterns', { params: status ? { status } : {} })
export const refreshPatterns = () =>
  http.post<{ patterns: BehaviorPattern[] }>('/api/review/patterns/refresh', null, { timeout: 120_000 })
export const updatePatternStatus = (id: number, status: string) =>
  http.patch<BehaviorPattern>(`/api/review/patterns/${id}/status`, { status })
```

### 步骤 3：Pinia Store

新建 `frontend/src/stores/review.ts`：

- reviews: Ref<TradeReview[]>
- stats: Ref<ReviewStats | null>
- patterns: Ref<BehaviorPattern[]>
- currentReview: Ref<TradeReview | null>
- loading: Ref<boolean>
- patternLoading: Ref<boolean>
- error: Ref<string | null>

Actions：
- fetchReviews(tsCode?)
- fetchReviewDetail(id)
- generateReview(tsCode) — 调用 API，成功后刷新列表
- saveNotes(id, notes)
- removeReview(id) — 删除后刷新列表
- fetchStats()
- fetchPatterns(status?)
- refreshPatterns() — 调用 API，成功后刷新 patterns
- updatePatternStatus(id, status)

验证：`cd frontend && pnpm type-check && pnpm build` 通过。
```

---

### Prompt C2：前端页面 + 组件 + 集成

```
你在 stock-assistant 项目中工作，正在开发 V7 前端页面。

请先阅读 `docs/V7_架构设计与开发计划.md` 第 4 节了解页面和组件设计。

### 步骤 1：ScoreRadar 雷达图组件

新建 `frontend/src/components/review/ScoreRadar.vue`：

- Props:
  - scores: ReviewScores（8 维度分数）
  - size?: number（图表宽高，默认 300）
- 使用 ECharts radar 图表：
  - indicator: 8 个轴，max=10，中文标签（入场时机、离场时机、止损纪律、止盈执行、仓位管理、持仓周期、交易纪律、盈亏比）
  - 数据填充区域颜色：根据均分变化
    - 均分 >= 7：绿色系 rgba(103, 194, 58, 0.3)
    - 均分 4-7：蓝色系 rgba(64, 158, 255, 0.3)
    - 均分 < 4：红色系 rgba(245, 108, 108, 0.3)
- 使用 `<script setup lang="ts">`
- 参考 `frontend/src/components/KlineChart.vue` 的 ECharts 初始化模式

### 步骤 2：PatternCard 行为模式卡片组件

新建 `frontend/src/components/review/PatternCard.vue`：

- Props:
  - pattern: BehaviorPattern
- 显示：
  - 标题
  - 类型标签：strength → el-tag type="success"，weakness → el-tag type="danger"
  - 描述文本
  - 关联维度（如有）
  - 状态标签：active / resolved / dismissed
- 操作按钮（仅 active 状态显示）：
  - "标记已解决" → emit update-status(id, "resolved")
  - "忽略" → emit update-status(id, "dismissed")
- 使用 `<script setup lang="ts">`

### 步骤 3：ReviewView 复盘主页面

新建 `frontend/src/views/ReviewView.vue`：

**顶部统计区**：
- 4 个 el-statistic 卡片行：
  - 复盘总数 (total_reviews)
  - 平均评分 (avg_overall_score，保留 1 位小数)
  - 最强维度 (best_dimension 中文名 + 分数)
  - 最弱维度 (worst_dimension 中文名 + 分数)
- onMounted 时调用 fetchStats()

**主体 Tab 切换**（el-tabs）：

Tab 1：复盘列表
- 每条复盘一张 el-card：
  - 头部：股票名称 + 代码
  - 内容：
    - 交易区间：first_trade_date ~ last_trade_date（持仓 N 天）
    - 盈亏：realized_pnl（盈绿亏红，使用 el-text type）
    - 交易笔数
    - 总评分：overall_score / 10（el-rate 组件只读，或数值+星级）
  - 操作：查看详情、删除（el-popconfirm）
- 空状态："暂无复盘记录，前往持仓页面生成复盘"
- 点击"查看详情" → 弹出 el-dialog：
  - ScoreRadar 组件显示雷达图
  - 各维度分数表格（维度名 + 分数 + 进度条）
  - LLM 综合分析（使用 v-html 渲染 Markdown，需 import marked）
  - 改进建议
  - 用户反思：el-input type="textarea"，带"保存"按钮
  - 底部：关闭按钮

Tab 2：行为模式
- 顶部："刷新行为模式分析"按钮（el-button, loading 状态）
- PatternCard 组件列表
- 空状态："需至少 3 条复盘记录才能分析行为模式"

### 步骤 4：路由与导航

1. `frontend/src/router/index.ts`：添加路由
   ```typescript
   import ReviewView from '../views/ReviewView.vue'
   // routes 数组中添加：
   { path: '/review', name: 'review', component: ReviewView }
   ```

2. `frontend/src/components/AppSidebar.vue`：
   - 添加"交易复盘"导航项，放在"持仓"下方

### 步骤 5：PositionView 集成

修改 `frontend/src/views/PositionView.vue`：

在已清仓（status="closed"）的持仓卡片中：
- 添加"生成复盘"按钮（el-button type="primary" size="small"）
- 点击调用 reviewStore.generateReview(ts_code)
- 生成成功后跳转到 /review 页面
- 如果该股已有复盘记录，改为显示"查看复盘"按钮 + 总评分

实现方式：
- 在 PositionView onMounted 时调用 reviewStore.fetchReviews()
- 用 computed 创建 reviewMap: Record<string, TradeReview>（ts_code → 最新复盘）
- 在卡片渲染时根据 reviewMap 判断显示哪个按钮

验证：`cd frontend && pnpm type-check && pnpm build` 通过。
```

---

## Phase D：集成验证

### Prompt D：集成联调与文档

```
你在 stock-assistant 项目中工作，V7 功能已开发完成，现在做最终集成验证。

### 步骤 1：全量测试

运行以下命令并确保全部通过：
```bash
cd backend && uv run pytest tests/ -v
cd frontend && pnpm type-check
cd frontend && pnpm build
```

如果有失败，修复后重新运行，直到全部通过。

### 步骤 2：更新 CLAUDE.md

在 CLAUDE.md 中：
1. 确认版本描述已更新为 V7
2. 在文档入口添加 V7 文档：
   - `docs/V7_架构设计与开发计划.md`：V7 架构与设计
   - `docs/V7_Codex提示词.md`：V7 执行提示词
   - `docs/V7_验收与回归指南.md`：V7 验收步骤
   - `docs/V7_执行顺序与提交建议.md`：V7 执行顺序
3. 添加 V7 相关约定：
   - 复盘 API 清单
   - V7 新增前端页面路由：/review
4. 更新 V7 最低验收标准（从 docs/V7_架构设计与开发计划.md §8 复制）

### 步骤 3：更新 docs/README.md

在 README.md 中：
1. 添加 V7 主文档区块（参照 V6 格式）
2. 将 V6 文档移到"历史版本文档"区块

### 步骤 4：验证功能完整性

列出以下检查清单并逐项确认：
- [ ] GET /api/health 返回 version 7.0.0
- [ ] position.py 中 all_positions 变量名已修复
- [ ] POST /api/review/generate/{ts_code} 可调通（mock LLM 或真实调用）
- [ ] GET /api/review 返回复盘列表
- [ ] GET /api/review/{id} 返回复盘详情
- [ ] PUT /api/review/{id}/notes 更新反思成功
- [ ] DELETE /api/review/{id} 删除成功
- [ ] GET /api/review/stats 返回统计数据
- [ ] GET /api/review/patterns 返回模式列表
- [ ] POST /api/review/patterns/refresh 可调通（mock 或真实）
- [ ] PATCH /api/review/patterns/{id}/status 更新状态成功
- [ ] 旧的 trade/position/plan API 全部正常
- [ ] 前端 /review 页面可正常渲染
- [ ] 前端 PositionView 已清仓卡片有"生成复盘"按钮

### 步骤 5：提交

```bash
git add -A
git commit -m "feat: V7 复盘与行为模式识别 — 8维度评分、LLM复盘Agent、雷达图、模式分析"
```
```

---

## 给 Codex 的全局指令（放在 Codex 的 system prompt 或项目说明中）

```
## 项目信息
- 项目路径：D:\构想\stock-assistant
- 技术栈：Python FastAPI + SQLAlchemy + SQLite（后端），Vue 3 + TypeScript + Element Plus + ECharts（前端）
- 后端包管理：uv，运行测试：cd backend && uv run pytest tests/ -v
- 前端包管理：pnpm，类型检查：cd frontend && pnpm type-check，构建：cd frontend && pnpm build
- 当前分支：codex/v7

## 必读文件（每个任务开始前）
1. CLAUDE.md — 项目规则、架构约定、Token 规则
2. docs/V7_架构设计与开发计划.md — V7 完整设计

## 代码风格
- 后端：Python 3.12+，type hints，SQLAlchemy 2.0 ORM
- 前端：Vue 3 <script setup lang="ts">，Pinia，Element Plus，ECharts
- tsconfig 开启了 noUncheckedIndexedAccess，数组下标访问类型为 T | undefined
- 错误响应统一使用 app/errors.py 的 build_error() 和 raise_service_error()
- LLM Agent 统一使用 agents/base.py 的 _safe_llm_call() 和 _extract_first_json_payload()
- Markdown 渲染使用 marked 库（前端已有依赖）
- 不要添加不必要的注释、docstring、类型注解到你没改的代码
- 不要引入新依赖，除非任务明确要求

## 子代理使用策略
- 使用子代理模式（--subtask / agent mode），每个 Prompt 块视为一个独立子代理任务
- Phase A 的 2 个任务可并行启动
- Phase B (B1→B2→B3→B4) 严格顺序执行
- Phase C (C1→C2) 严格顺序执行
- Phase D 在 B + C 全部完成后执行
- 每个任务完成后都要运行对应的验证命令
- 如果测试失败，在当前子代理内修复，不要跳到下一个任务
```
