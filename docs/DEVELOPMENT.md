# TradeLoop · 知行盘开发约定

## 项目概览

- 项目名称：TradeLoop · 知行盘
- 当前公开基线：V8
- 默认主分支：`main`
- 技术栈：
  - 后端：FastAPI + SQLAlchemy + SQLite
  - 前端：Vue 3 + TypeScript + Pinia + Element Plus + ECharts

## 文档入口

- `README.md`（仓库根）：项目介绍、快速开始、架构图
- `docs/domain/`：交易闭环·费用·持仓、选股引擎等金融逻辑设计文档（中英双语）
- `docs/api/`：OpenAPI 契约
- `CHANGELOG.md`：版本演进

## 开发原则

### 先分析，再修复

- 遇到问题先找根因，再决定修补还是重构。
- 如果问题属于结构性设计缺陷，优先重构局部结构，不要堆临时补丁。
- 不在没读代码的情况下直接下结论。

### 模块化优先

- 新功能默认拆为：类型层、API 层、store/service 层、页面/路由层。
- 尽量避免让页面直接拼复杂数据；复杂数据处理优先下沉到 store 或 service。
- 新模型、新 API、新页面尽量成组出现，减少跨模块隐式依赖。

### 默认使用 Git

- 所有开发工作默认纳入 Git 管理。
- 较大版本按执行包提交，优先保证每个提交点可回归、可回退。

## 后端约定

### 数据模型

- 新增 SQLAlchemy 模型后，必须同步导出到 `backend/app/models/__init__.py`。
- 否则测试里的 `Base.metadata.create_all()` 不会创建对应表。
- V8 新增数据表：
  - `daily_indicator`：22 个预计算技术指标字段
  - `daily_moneyflow`：个股资金流向
  - `top_list` / `top_list_detail`：龙虎榜汇总与营业部明细
- `stock_financial` 在 V8 中改为全字段模型，必须保留 `profit_dedt` 和 `revenue` 以兼容旧筛选逻辑。

### 错误处理

- 服务层统一返回正常结果或 `build_error(...)`。
- API 层统一通过 `raise_service_error(...)` 把服务错误转换为 HTTP 响应。

### 默认配置

- 用户配置统一放在 `user_config`。
- 当前 V6 默认配置至少包括：
  - `total_capital`
  - `commission_rate`
  - `stamp_tax_rate`
  - `transfer_fee_rate`
- V8 数据同步配置：
  - `history_start_date`
  - `backfill_sleep`

### 单位换算

- `daily_quote.amount` 存储单位：千元
- 千元转亿元：`amount / 100_000`
- `daily_quote.total_mv` 存储单位：万元
- 万元转亿元：`total_mv / 10_000`

### V8 指标参数

- MA：`5, 10, 20, 60, 120, 240`
- MACD：`12, 26, 9`
- KDJ：`9, 3, 3`
- RSI：`6, 12, 24`
- BOLL：`20, 2`
- ATR：`14`

### 交易与持仓规则

- 交易记录表：`trade_record`
- 持仓表：`position`
- 删除交易记录后，不做逆向回滚，固定走 `recalculate_position(ts_code)` 全量重算。
- 买入且关联 `plan_id` 时，如果计划状态还是 `pending`，自动改成 `executed`。
- 卖出不会反向修改计划状态。

## 前端约定

- API 基础地址统一从 `VITE_API_URL` 读取，开发默认值为 `http://localhost:8000`。
- `usePlanStore` 只负责计划 CRUD。
- 计划生成和总资金配置放在 `usePlanGenerateStore`。
- V7+V8 页面：
  - `/trade`
  - `/position`
  - `/review`
  - `/sentiment`

## Token / 凭证规则

- 第三方 token 不在代码里硬编码；运行时统一经凭证层 `app/credentials.py` 解析：
  设置页填写存入本地 DB（覆盖 `config/local.toml`），保存即生效。
- 凭证键禁止经通用 `/api/config/{key}` 读写（会绕过打码），只走 `/api/credentials`。
- 需要 token 的 SDK 初始化时显式传入 `credentials.tushare_token()`，禁止无参调用。

## V8 同步约定

- `sync_daily()` 的顺序固定为：
  1. `sync_stock_basic()`
  2. `sync_daily_quotes()`
  3. `sync_moneyflow_daily()`
  4. `sync_toplist_daily()`
  5. `sync_limit_event_daily()`
  6. `sync_theme_heat_daily()`
  7. `sync_market_sentiment_daily()`
  8. `sync_indicators_daily()`
- 行情必须先于指标计算。
- 财务全字段同步与历史回填统一走全量/回填流程，不放进每日增量。
- 历史回填统一走 `backfill_all()`，并复用同步锁避免并发。

## 测试与验证

### 后端

- 运行命令：`cd backend && uv run python -m pytest tests/ -q`（务必 `python -m`）
- 新增功能优先走红绿测试闭环：先写失败测试，再写最小实现，再跑回归。

### 前端

- 类型检查：`cd frontend && pnpm type-check`
- 构建验证：`cd frontend && pnpm build`

## V7-V8 API 清单

- `POST /api/review/generate/{ts_code}`
- `GET /api/review`
- `GET /api/review/{id}`
- `PUT /api/review/{id}/notes`
- `DELETE /api/review/{id}`
- `GET /api/review/stats`
- `GET /api/review/patterns`
- `POST /api/review/patterns/refresh`
- `PATCH /api/review/patterns/{id}/status`
- `GET /api/dashboard/sentiment/summary`
- `GET /api/dashboard/sentiment/history`
- `GET /api/dashboard/sentiment/themes`
- `GET /api/dashboard/sentiment/detail/{trade_date}`

### V8 最低验收标准

1. 后端全量测试通过。
2. `/api/health` 返回 `version: "8.0.0"`。
3. `daily_indicator`、`daily_moneyflow`、`top_list`、`top_list_detail` 表结构正确。
4. `stock_financial` 已升级为全字段结构，字段数不少于 50。
5. `sync_daily()` 已接入资金流向、龙虎榜、指标计算。
6. `POST /api/data/backfill/trigger` 可触发历史回填。
7. V1-V7 旧测试与 V8 新测试全部通过。

## 备注

- 如果任务横跨多个模块，优先拆成可验证的小闭环。
