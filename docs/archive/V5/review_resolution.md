# V5 Review Resolution

| finding_id | severity | original_issue | resolution | status |
| --- | --- | --- | --- | --- |
| V5-001 | P1 | `PlanView` 把股票搜索响应当成数组，手动创建计划无法正常选股。 | 把 `searchStocks()` 统一改为 API 层直接返回 `StockSearchResult[]`，同时改造 `PlanView` 与 `WatchlistView`。 | fixed |
| V5-002 | P1 | `PlanAgent` 只校验“是否 3 个对象”，没有把仓位、方向、止盈比例和等业务规则前置。 | 新增 `plan_contract.py`，让 LLM proposal 与手动保存复用同一套校验逻辑；非法 proposal 直接走 `manual_fallback`。 | fixed |
| V5-003 | P2 | `generate` 把股票不存在、LLM 输出不可用、上游异常等都混在 `500` 里。 | API 层统一按 `error_type` 映射为 `404 / 400 / 502`，并把可恢复场景改为 `manual_fallback`。 | fixed |
| V5-004 | P2 | 前端缺少已保存 `pending` 计划的编辑入口，实际只有 CRD。 | `PlanView` 新增 `pending` 计划编辑入口，并复用共享 `PlanEditor`。 | fixed |
| V5-005 | P2 | `PlanView` 多数失败只写进 store，不在页面展示，用户容易感知为“没反应”。 | `PlanView`、`PlanGenerateView` 均新增页面级 `el-alert` 和关键动作失败提示。 | fixed |
| V5-006 | P3 | `total_capital` 默认值和 `status` 默认契约在 model / migration / API 三处不一致。 | 新增默认值迁移与 `ensure_default_configs()`，`TradingPlan.status` 改为 service 显式写入。 | fixed |
| V5-007 | P3 | 测试主要覆盖 service 层，没有压实 API 状态码、manual fallback 和新边界。 | 补充 API 测试文件 `test_v5_plan_api.py`，并扩展 `test_v5_plan.py` 的 LLM 解析边界。 | fixed |
