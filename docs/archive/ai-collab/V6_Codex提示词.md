# V6 Codex 执行提示词

本文件包含交给 Codex 的分阶段提示词。每个提示词设计为一个独立子代理任务。
Codex 应默认使用子代理模式执行，每个 Phase 内的任务可并行。

> **使用方式**：把每个 `### Prompt` 块的内容直接粘贴给 Codex 作为任务描述。

---

## Phase A：技术债清理（7 个并行任务）

> Phase A 的所有任务互相独立，可同时启动。完成后统一运行 `cd backend && uv run pytest tests/ -v` 和 `cd frontend && pnpm build` 验证无回归。

---

### Prompt A1：提取单位转换常量

```
你在 stock-assistant 项目中工作。请完成以下重构，不改变任何功能行为：

1. 新建文件 `backend/app/constants.py`，定义：
   - `AMOUNT_UNIT_TO_YI = 100_000`  # daily_quote.amount 千元 → 亿元
   - `MV_UNIT_TO_YI = 10_000`       # total_mv 万元 → 亿元
   并添加注释说明单位换算逻辑。

2. 在以下所有文件中，将硬编码的 `100_000` 和 `10_000`（用于单位换算的场景）替换为导入的常量：
   - backend/app/services/screening.py
   - backend/app/api/stocks.py
   - backend/app/services/kline.py
   - backend/app/services/market.py
   - backend/app/services/agents.py（现在是 agents/ 目录下的文件，注意适配路径）
   - backend/app/services/watchlist.py
   - backend/app/services/conditions/amount_gt.py
   - backend/app/services/conditions/market_cap_gt.py

注意：
- 只替换用于"金额单位换算"的 100_000 和 10_000。有些地方的数字可能有其他含义（如 limit 数量），不要替换。
- 用 grep 搜索 `100_000` 和 `10_000` 确认每一处的语义后再替换。
- 替换完成后运行 `cd backend && uv run pytest tests/ -v` 确保全部通过。
```

---

### Prompt A2：统一错误响应契约

```
你在 stock-assistant 项目中工作。请完成以下重构：

1. 新建 `backend/app/errors.py`，将 `backend/app/services/plan_contract.py` 中的 `build_error()` 函数提升为全局共享工具：
   ```python
   def build_error(message: str, error_type: str = "validation") -> dict[str, Any]:
       return {"error": message, "error_type": error_type}
   ```

2. 在 `plan_contract.py` 中改为 `from app.errors import build_error`，删除本地定义。

3. 检查以下文件中所有返回错误 dict 的位置（搜索 `{"error":` 和 `return {"error"`），统一改为使用 `build_error()`：
   - backend/app/services/plan.py（已在用，确认 import 路径更新）
   - backend/app/services/agents.py 的所有 agent 函数
   - backend/app/services/screening.py
   - backend/app/services/watchlist.py
   - backend/app/services/data_sync.py（如果有）

4. 在 `backend/app/api/plan.py` 中已有 `_raise_plan_error()` 函数，将其提升到 `errors.py` 中作为 `raise_service_error(result: dict)` 供所有 API 路由复用。更新所有 api/*.py 中的错误处理代码。

验证：`cd backend && uv run pytest tests/ -v` 全部通过，功能行为完全不变。
```

---

### Prompt A3：消除原始 SQL 元组访问

```
你在 stock-assistant 项目中工作。请完成以下重构：

搜索后端代码中所有使用 `db.execute(text(...))` 并通过 `row[0]`, `row[1]` 等下标访问结果的位置。将它们改为以下两种方式之一：
- 优先：使用 SQLAlchemy ORM `db.query(Model)` 或 `db.get(Model, pk)`
- 次选：使用 `.mappings().fetchone()` 返回字典，通过 `row["column_name"]` 访问

重点检查以下文件：
- backend/app/api/stocks.py（get_stock_detail 函数里有 raw SQL）
- backend/app/services/watchlist.py（_stock_query_with_quote 函数使用 f-string 拼 SQL）
- backend/app/services/market.py（有 raw SQL 查询）

对于 watchlist.py 中的 `_stock_query_with_quote()` 函数：它用 f-string 拼接 WHERE 子句，这是一个潜在的 SQL 注入风险点。请改为参数化查询或 ORM 查询。

验证：`cd backend && uv run pytest tests/ -v` 全部通过。
```

---

### Prompt A4：agents.py 拆分与 MA 复用

```
你在 stock-assistant 项目中工作。当前 `backend/app/services/agents.py` 有 600+ 行，包含 6 个日报 Agent 和 1 个 PlanAgent，且 MA 计算逻辑重复出现。请拆分重构：

1. 新建 `backend/app/services/indicators.py`，提取技术指标计算工具函数：
   - `calc_ma(closes: list[float], period: int) -> float` — 计算移动平均
   - `calc_price_stats(quotes) -> dict` — 从 quote 列表计算 ma5/ma20/ma60/high/low/pct_change 等常用指标
   这些函数在 agents.py 中至少出现了 2 次（StockAgent 和 PlanAgent 各算一遍 MA）。

2. 将 `agents.py` 拆分为目录结构：
   ```
   backend/app/services/agents/
   ├── __init__.py     # 导出 run_daily_report, run_stock_agent, run_plan_agent 等公共接口
   ├── base.py         # 共享工具：_SYSTEM_PROMPT, _safe_llm_call(), _extract_first_json_payload()
   ├── daily.py        # 6 个日报 Agent（MacroAgent, SectorAgent, FlowAgent, TechnicalAgent, RiskAgent, SummaryAgent）
   ├── stock.py        # StockAgent（个股分析）
   └── plan.py         # PlanAgent（交易计划生成）
   ```

3. 确保所有 import 这些函数的文件（api/analysis.py, api/plan.py, tests/ 等）都正确更新 import 路径。搜索 `from app.services.agents import` 和 `from app.services import agents` 找到所有引用。

4. `__init__.py` 中重新导出所有公共接口，保持外部调用代码最小改动：
   ```python
   from app.services.agents.daily import run_daily_report
   from app.services.agents.stock import run_stock_agent
   from app.services.agents.plan import run_plan_agent
   ```

验证：
- `cd backend && uv run pytest tests/ -v` 全部通过
- 功能完全不变，只是文件组织变了
```

---

### Prompt A5：Pydantic 模型加强输入校验

```
你在 stock-assistant 项目中工作。请加强 API 层的 Pydantic 输入校验：

1. `backend/app/api/plan.py`：
   - `StatusUpdate.status` 从 `str` 改为 `Literal["executed", "abandoned"]`
   - `PlanCreate.direction` 从 `str` 改为 `Literal["buy", "sell"]`
   - `PlanCreate.source` 从 `str` 改为 `Literal["llm_generated", "manual"]`
   - 添加必要的 `from typing import Literal` import

2. 检查其他 api/*.py 文件，找出类似的"接受任意字符串但实际只有几个合法值"的 Pydantic 字段，同样改为 Literal 类型。

注意：
- 不要改 service 层的校验逻辑，service 层的校验作为双重保险保留
- Literal 类型会让 Pydantic 在反序列化时自动返回 422（而不是进入 service 层返回 400），这是可接受的行为变化
- 运行 `cd backend && uv run pytest tests/ -v` 确保全部通过。如果有测试因为返回码从 400 变为 422 而失败，更新对应测试的断言。
```

---

### Prompt A6：前端 API baseURL 环境变量化

```
你在 stock-assistant 项目中工作。请完成以下前端重构：

1. 新建 `frontend/.env.development` 文件：
   ```
   VITE_API_URL=http://localhost:8000
   ```

2. 修改 `frontend/src/api/index.ts`，将硬编码的 baseURL 改为：
   ```typescript
   export const http = axios.create({
     baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
     timeout: 60000,
   })
   ```

3. 确认 `frontend/.gitignore` 中没有忽略 `.env.development`（这是可以入库的开发默认值）。如果有 `.env.local` 或 `.env.production` 的模式需要忽略，确保 `.gitignore` 只忽略 `.env.local`。

4. 如果 `frontend/src/vite-env.d.ts` 或 `frontend/env.d.ts` 存在，添加类型声明：
   ```typescript
   interface ImportMetaEnv {
     readonly VITE_API_URL: string
   }
   ```

验证：`cd frontend && pnpm type-check && pnpm build` 通过。
```

---

### Prompt A7：Plan Store 拆分

```
你在 stock-assistant 项目中工作。当前 `frontend/src/stores/plan.ts` 同时管理三类状态：计划列表管理、LLM 生成上下文、编辑草稿。请拆分：

1. 保留 `stores/plan.ts`，只保留计划 CRUD 相关状态和方法：
   - plans, currentPlan, loading, error
   - fetchPlans(), fetchPlanDetail(), savePlan(), editPlan(), changeStatus(), removePlan()

2. 新建 `stores/planGenerate.ts`，提取生成流程相关状态：
   - generateResult, proposals (computed), totalCapital
   - generate(), fetchTotalCapital(), clearGenerateResult()

3. 更新引用：
   - `views/PlanView.vue` → 只用 `usePlanStore`
   - `views/PlanGenerateView.vue` → 用 `usePlanStore`（保存时）+ `usePlanGenerateStore`（生成流程）
   - 搜索 `from '@/stores/plan'` 找到所有引用

4. 确保两个 store 之间没有循环依赖。如果 PlanGenerateView 保存时需要调用 plan store 的 savePlan，直接在 view 层组合调用两个 store。

验证：`cd frontend && pnpm type-check && pnpm build` 通过。
```

---

## Phase B：后端新功能（顺序执行）

> Phase B 依赖 Phase A 完成。B1-B4 按顺序执行，B5-B6 可与 B4 并行。

---

### Prompt B1-B4：后端交易记录与持仓核心

```
你在 stock-assistant 项目中工作，正在开发 V6（交易记录+持仓跟踪）。

请严格按照 `docs/V6_架构设计与重构计划.md` 中的设计执行以下工作。开始前先读完该文档的第 2-3 节。

同时务必阅读项目规则 `CLAUDE.md`，遵守其中的所有约定（特别是 Token 规则、架构约定、测试规范）。

### 步骤 1：数据模型 + 迁移

1. 新建 `backend/app/models/trade.py`，定义 `TradeRecord` 和 `Position` 两个模型，严格按照设计文档 §2.1 和 §2.2 的字段定义。
2. 在 `backend/app/models/__init__.py` 中导出新模型（必须，否则 create_all 不会建表）。
3. 新建 Alembic migration：
   - 创建 trade_record 表和 position 表
   - 在 user_config 中插入费率默认值（commission_rate, stamp_tax_rate, transfer_fee_rate）
   - 使用 INSERT ... WHERE NOT EXISTS 模式保证幂等

### 步骤 2：交易记录服务

新建 `backend/app/services/trade_contract.py`（校验契约，参考 plan_contract.py 的模式）：
- validate_trade_payload(data) — 校验必填字段、方向、价格>0、数量>0
- 卖出时校验：卖出数量 ≤ 当前持仓量

新建 `backend/app/services/trade.py`：
- create_trade(db, data) — 核心逻辑见设计文档 §3.2
  - 保存记录
  - 买入：创建/更新 Position，avg_cost = total_cost / total_quantity
  - 卖出：计算 realized_pnl = (sell_price - avg_cost) × quantity - fee，扣减持仓
  - 清仓（quantity==0）→ status="closed"
  - 如有 plan_id 且 direction=="buy" → 自动更新 plan.status 为 "executed"
- get_trades(db, ts_code, direction, date_from, date_to) — 列表查询
- get_trade_detail(db, trade_id) — 详情
- delete_trade(db, trade_id) — 删除 + 重算持仓

新建 `backend/app/services/position.py`：
- get_positions(db, status) — 持仓列表
- get_position_detail(db, ts_code) — 个股持仓（含关联交易记录）
- get_position_summary(db) — 汇总（总市值需要读最新行情）
- recalculate_position(db, ts_code) — 从该股所有交易记录重新计算持仓

### 步骤 3：API 路由

新建 `backend/app/api/trade.py` 和 `backend/app/api/position.py`，路由定义见设计文档 §3.1。

在 `backend/app/main.py` 中注册新路由：
```python
app.include_router(trade.router, prefix="/api")
app.include_router(position.router, prefix="/api")
```

使用 Literal 类型约束 Pydantic 输入模型（direction: Literal["buy", "sell"] 等）。
错误处理使用 `app/errors.py` 中的 `build_error()` 和 `raise_service_error()`。

### 步骤 4：测试

新建 `backend/tests/test_v6_trade.py` 和 `backend/tests/test_v6_position.py`，覆盖：

交易记录测试：
- 买入记录创建成功，持仓自动生成
- 加仓后 avg_cost 正确（加权平均）
- 卖出后 realized_pnl 正确
- 清仓后 position.status == "closed"
- 再次买入同一股票，position reopen
- 卖出数量超过持仓量 → 400 错误
- 关联 plan_id 买入 → plan.status 自动变为 executed
- 删除交易记录 → 持仓正确回滚
- 边界：price=0 → 400，quantity=0 → 400，direction 非法 → 400/422

持仓测试：
- 持仓列表按 status 筛选
- 持仓汇总数值正确
- recalculate 后结果与逐条计算一致

运行 `cd backend && uv run pytest tests/ -v` 确保全部通过（包括 V1-V5 的旧测试）。
```

---

## Phase C：前端新功能（顺序执行）

> Phase C 依赖 Phase B 完成。

---

### Prompt C1-C3：前端类型 + Store + 交易表单组件

```
你在 stock-assistant 项目中工作，正在开发 V6 前端。

请先阅读 `docs/V6_架构设计与重构计划.md` 第 4 节了解前端架构设计，以及 `CLAUDE.md` 了解前端规范（特别是 noUncheckedIndexedAccess 规则）。

### 步骤 1：类型定义

新建 `frontend/src/types/trade.ts`，定义以下接口（字段与后端模型对齐）：
- TradeRecord
- TradeCreateData（创建交易的请求体）
- TradeListFilter（列表筛选参数）
- Position
- PositionWithQuote（扩展 current_price, unrealized_pnl, unrealized_pnl_pct, market_value）
- PositionSummary

### 步骤 2：API 封装

在 `frontend/src/api/index.ts` 中新增交易和持仓相关 API 函数：
- createTrade(data)
- getTrades(filter)
- getTradeDetail(id)
- deleteTrade(id)
- getPositions(status)
- getPositionDetail(tsCode)
- getPositionSummary()
- recalcPosition(tsCode)

### 步骤 3：Pinia Store

新建 `frontend/src/stores/trade.ts`：
- trades ref, loading, error
- fetchTrades(filter), createTrade(data), deleteTrade(id)

新建 `frontend/src/stores/position.ts`：
- positions ref, summary ref, loading, error
- fetchPositions(status), fetchSummary(), fetchDetail(tsCode)

### 步骤 4：交易表单组件

新建 `frontend/src/components/trade/TradeForm.vue`：
- Props: initialData?（预填数据，从计划跳转时用）、mode: 'create'
- 股票搜索选择（复用 searchStocks API）
- 方向选择 radio（买入/卖出）
- 价格、数量输入（el-input-number）
- 日期选择（el-date-picker）
- 关联计划下拉（可选，按 ts_code 过滤 pending/executed 计划）
- 费用自动计算区域（读 UserConfig 费率，实时显示：佣金 + 印花税 + 过户费 = 总费用）
  - 自动计算值可手动覆盖
- 金额 = price × quantity 实时预览
- emit: submit(data), cancel()

验证：`cd frontend && pnpm type-check && pnpm build` 通过。
```

---

### Prompt C4-C6：前端页面 + 集成改造

```
你在 stock-assistant 项目中工作，正在开发 V6 前端页面。

请先阅读 `docs/V6_架构设计与重构计划.md` 第 4-5 节了解页面设计和交互流程。

### 步骤 1：交易记录页

新建 `frontend/src/views/TradeRecordView.vue`：
- 顶部工具栏：
  - 日期范围选择器（el-date-picker type="daterange"）
  - 方向筛选 select（全部/买入/卖出）
  - "录入交易"按钮 → 弹出 TradeForm 对话框
- 主体 el-table：日期、股票、方向（买入绿/卖出红标签）、价格、数量、金额、费用、备注
  - 操作列：查看详情、删除（确认弹框）
- 空状态提示

### 步骤 2：持仓全景页

新建 `frontend/src/views/PositionView.vue`：
- 顶部汇总卡片行（4 个 el-statistic）：
  - 总市值、总成本、总浮盈浮亏（盈绿亏红）、持仓只数
- Tab 切换：当前持仓 / 已清仓
- 卡片列表（el-card）：每只股票一张卡片：
  - 股票名称 + 代码
  - 持仓量 / 均价 / 当前价 / 市值
  - 浮盈浮亏金额和百分比（盈绿亏红）
  - 操作：卖出按钮、查看交易记录
  - 点击卡片进入详情（对话框或侧边抽屉），展示：
    - 持仓概要
    - 该股交易记录时间线

### 步骤 3：现有页面改造与路由

1. `frontend/src/router/index.ts`：添加 /trade 和 /position 路由
2. `frontend/src/components/AppSidebar.vue`：添加"交易记录"和"持仓"导航项，放在"交易计划"下方
3. `frontend/src/views/PlanView.vue`：在 pending 状态的计划卡片中添加"录入交易"按钮，点击弹出 TradeForm 并预填（股票、方向=buy、关联 plan_id）
4. `frontend/src/views/StockDetailView.vue`：如果该股有持仓，在页面中显示持仓信息区块
5. `frontend/src/views/SettingsView.vue`：添加"交易费率"设置区（佣金费率、印花税率、过户费率三个输入框）

验证：`cd frontend && pnpm type-check && pnpm build` 通过。
```

---

## Phase D：集成验证

### Prompt D：集成联调与文档

```
你在 stock-assistant 项目中工作，V6 功能已开发完成，现在做最终集成验证。

### 步骤 1：全量测试

运行以下命令并确保全部通过：
```bash
cd backend && uv run pytest tests/ -v
cd frontend && pnpm type-check
cd frontend && pnpm build
```

如果有失败，修复后重新运行。

### 步骤 2：更新 CLAUDE.md

在 CLAUDE.md 中：
1. 将项目概述中的版本描述更新为 V6
2. 添加 V6 验收标准（从 docs/V6_架构设计与重构计划.md §8 复制）
3. 如果 agents 已拆分为目录结构，更新相关约定描述

### 步骤 3：更新文档索引

在 CLAUDE.md 的版本文档索引中添加：
- `docs/V6_架构设计与重构计划.md` — V6 交易记录+持仓+重构设计

在 `docs/README.md` 中添加 V6 文档条目。

### 步骤 4：验证功能完整性

列出以下检查清单并逐项确认（在后端 test 和前端 build 基础上）：
- [ ] GET /api/health 返回 version 6.0.0
- [ ] POST /api/trade 创建交易记录成功
- [ ] GET /api/position 返回持仓列表
- [ ] GET /api/position/summary 返回汇总
- [ ] 旧的 plan API 全部正常（GET/POST/PUT/PATCH/DELETE）
- [ ] 旧的 watchlist、screening、analysis API 全部正常
```

---

## 给 Codex 的全局指令（放在 Codex 的 system prompt 或项目说明中）

```
## 项目信息
- 项目路径：D:\构想\stock-assistant
- 技术栈：Python FastAPI + SQLAlchemy + SQLite（后端），Vue 3 + TypeScript + Element Plus（前端）
- 后端包管理：uv，运行测试：cd backend && uv run pytest tests/ -v
- 前端包管理：pnpm，类型检查：cd frontend && pnpm type-check，构建：cd frontend && pnpm build
- 当前分支：v6-dev

## 必读文件（每个任务开始前）
1. CLAUDE.md — 项目规则、禁止事项、架构约定、Token 规则
2. docs/V6_架构设计与重构计划.md — V6 完整设计

## 代码风格
- 后端：Python 3.12+，type hints，SQLAlchemy 2.0 ORM
- 前端：Vue 3 <script setup lang="ts">，Pinia，Element Plus
- tsconfig 开启了 noUncheckedIndexedAccess，数组下标访问类型为 T | undefined
- 错误响应统一使用 app/errors.py 的 build_error()
- 不要添加不必要的注释、docstring、类型注解到你没改的代码
- 不要引入新依赖，除非任务明确要求

## 子代理使用策略
- 每个 Prompt 块视为一个独立子代理任务
- Phase A 的 7 个任务可全部并行启动
- Phase B 和 C 按顺序执行
- 每个任务完成后都要运行对应的验证命令
- 如果测试失败，在当前子代理内修复，不要跳到下一个任务
```
