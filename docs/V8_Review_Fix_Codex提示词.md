# V8 审查修复 — Codex 执行提示词

> 审查时间：2026-04-08
> 背景：V8 主体开发 + 市场情绪升级完成后，全面代码审查发现的遗留问题。
> 旧清单 `V8_Code_Review_Issues.md` 中 23 个问题已修复 15 个，本文件合并剩余旧问题 + 新发现问题，按执行包拆分。

---

## 给 Codex 的全局指令

```
## 项目信息
- 项目路径：stock-assistant（当前工作目录）
- 技术栈：Python FastAPI + SQLAlchemy + SQLite（后端）；Vue 3 + TypeScript + Pinia + Element Plus（前端）
- 后端测试：cd backend && uv run pytest tests/ -v
- 前端类型检查：cd frontend && pnpm type-check
- 前端构建验证：cd frontend && pnpm build
- 当前分支：codex/v8

## 必读文件（每个任务开始前）
1. CLAUDE.md — 项目规则、架构约定
2. docs/V8_Code_Review_Issues.md — 旧问题清单（已修大部分，参考上下文）

## 代码风格
- Python 3.12+，type hints，SQLAlchemy 2.0 ORM
- 错误响应统一用 app/errors.py 的 build_error() 和 raise_service_error()
- Tushare token 从 config 显式传入，不依赖环境变量
- 前端 TypeScript strict，避免 any 类型
- 不要添加不必要的注释、docstring 到没改的代码
- 不要引入新依赖

## 执行策略
- Phase 1 和 Phase 2 可并行（后端 / 前端独立）
- Phase 3 依赖 Phase 1 + 2 完成
- 每个任务完成后运行对应验证命令
- 如果测试失败，在当前任务内修复
```

---

## Phase 1：后端修复（5 个任务）

### Prompt 1-1：数据同步事务与锁加固

```
你在 stock-assistant 项目中工作。修复以下后端数据同步问题：

## 任务 1：sync_daily() 中的财务数据调用问题
- 文件：backend/app/services/data_sync.py
- 问题：sync_financial_data() 是全量同步（DELETE 全表 + INSERT），但被放在每日增量 sync_daily() 中调用
- 修复：将 sync_financial_data() 从 sync_daily() 中移除。财务数据只应在 backfill 流程中全量更新，不应每日运行

## 任务 2：同步服务返回格式统一
- 文件：backend/app/services/sync_moneyflow.py 和 backend/app/services/sync_toplist.py
- 问题：sync_moneyflow_daily() 返回 failed_dates 列表，sync_toplist_daily() 不返回
- 修复：让 sync_toplist_daily() 也返回 (total_rows, failed_dates) 元组，和 moneyflow 一致

## 任务 3：session 管理一致性
- 文件：backend/app/services/data_sync.py
- 问题：有的函数用 SessionLocal() + try-finally 关闭，有的不关闭
- 修复：统一用 try-finally 确保 session 关闭，或改用 contextmanager

## 验证
cd backend && uv run pytest tests/ -v
确保所有测试通过。如果 sync_daily 的测试因为移除 financial 调用而失败，更新对应测试。
```

---

### Prompt 1-2：重复定义与硬编码清理

```
你在 stock-assistant 项目中工作。清理以下代码重复和硬编码问题：

## 任务 1：get_db() 重复定义
- 文件：backend/app/api/analysis.py（约第 33 行）
- 问题：自己定义了 get_db()，但 backend/app/database.py 已导出同名函数
- 修复：删除 analysis.py 中的 get_db() 定义，改为 from app.database import get_db
- 注意：检查所有 api/*.py 文件，如果还有其他文件也重复定义了 get_db()，一并修复

## 任务 2：kline.py 的 DESC + reverse 性能浪费
- 文件：backend/app/services/kline.py（约第 54-62 行）
- 问题：查询用 ORDER BY trade_date DESC，拿到后又 list(reversed(rows))
- 修复：直接用 ASC 排序，去掉 reverse

## 任务 3：日志格式统一
- 文件：backend/app/services/ 下所有同步服务（data_sync.py, sync_indicator.py, sync_moneyflow.py, sync_toplist.py, backfill.py 等）
- 问题：print() 和 logger 混用，格式各异
- 修复：
  1. 确保每个服务文件顶部有 logger = logging.getLogger(__name__)
  2. 把所有 print("[sync]...") 改为 logger.info(...)
  3. 把所有 print("[backfill]...") 改为 logger.info(...)
  4. 异常处使用 logger.exception(...)
  5. 不要改动非同步服务的文件

## 验证
cd backend && uv run pytest tests/ -v
```

---

### Prompt 1-3：TopList 唯一约束 + API 导出清理

```
你在 stock-assistant 项目中工作。修复以下数据模型和 API 层问题：

## 任务 1：TopList 加数据库层唯一约束
- 文件：backend/app/models/top_list.py
- 问题：仅靠应用层 _dedupe_top_list_rows() 防止重复，数据库没有唯一约束做安全网
- 修复：
  1. 在 TopList 模型上加 UniqueConstraint('ts_code', 'trade_date', 'reason', name='uq_toplist_ts_date_reason')
  2. 新建 Alembic 迁移文件添加该约束
  3. 注意：如果现有数据有重复行，先在迁移的 upgrade() 中去重再加约束

## 任务 2：api/__init__.py 导出补全
- 文件：backend/app/api/__init__.py
- 问题：__all__ 只有 ["review"]，但 main.py import 了 13 个 router
- 修复：把 __all__ 补全为所有实际使用的 router 名

## 任务 3：CORS 收紧
- 文件：backend/app/main.py（CORS 中间件配置处）
- 问题：allow_methods=["*"] 和 allow_headers=["*"] 过于宽泛
- 修复：allow_methods 改为 ["GET", "POST", "PUT", "PATCH", "DELETE"]，allow_headers 改为 ["Content-Type", "Authorization"]

## 验证
cd backend && uv run pytest tests/ -v
```

---

### Prompt 1-4：指标计算边界修复

```
你在 stock-assistant 项目中工作。修复指标计算的边界问题：

## 任务 1：sync_indicator.py 的 per-stock 错误隔离
- 文件：backend/app/services/sync_indicator.py（sync_indicators_daily 函数）
- 问题：如果某只股票的 calculate_stock_indicators() 抛异常，整批失败
- 修复：在遍历 ts_codes 的循环中，对每只股票加 try-except，异常时 logger.warning 跳过该股票，不中断整批

## 任务 2：indicator_calc.py 浮点精度说明
- 文件：backend/app/services/indicator_calc.py
- 问题：多次 float 运算在长期回填时可能有精度偏差
- 修复：在文件顶部加一行注释说明设计决策：# 注意：指标均使用 float 计算，长期序列可能有微小精度偏差，这在技术分析场景下可接受

## 任务 3：配置矛盾修复
- 文件：config/default.toml
- 问题：history_years = 3 和 history_start_date = "20140101" 逻辑矛盾（3年 vs 12年）
- 修复：
  1. 删除 history_years，统一用 history_start_date 控制回填起点
  2. 检查代码中是否有地方读取 history_years，如有则改为读取 history_start_date
  3. history_start_date 的值保持 "20140101" 不变

## 验证
cd backend && uv run pytest tests/ -v
```

---

### Prompt 1-5：CLAUDE.md 文档更新

```
你在 stock-assistant 项目中工作。更新项目文档使其与当前代码一致：

## 任务 1：CLAUDE.md 更新
- 文件：CLAUDE.md
- 修改项：
  1. 第 98-101 行的 V7 页面列表，改为 V7+V8 页面（加上 /sentiment）
  2. 第 133-143 行的"V7 API 清单"标题改为"V7-V8 API 清单"，补充 V8 新增的 API 端点（sentiment 相关的 GET/POST 接口，从 backend/app/api/sentiment.py 中提取）
  3. 确认第 109-119 行的 V8 同步约定与实际 sync_daily() 代码一致（如果 Phase 1-1 移除了财务同步，这里也要同步更新）

## 任务 2：V8_Code_Review_Issues.md 状态更新
- 文件：docs/V8_Code_Review_Issues.md
- 修改项：在每个已修复的问题标题后加 ✅，未修复的保持原样
- 已修复清单：C2, C3, C4, C5, H1, H2, H3, H4, H5, H6, M1, M3, M5, M6
- 仍存问题（本轮修复中）：C1(实际已修复，确认后标记), M2, L2, L5, M4

## 不要改其他文件。
## 验证：无需运行测试，只是文档更新。
```

---

## Phase 2：前端修复（3 个任务）

### Prompt 2-1：Store 层错误处理统一

```
你在 stock-assistant 项目中工作。修复前端 Store 层的错误处理问题：

## 任务 1：Watchlist Store 操作结果反馈
- 文件：frontend/src/stores/watchlist.ts
- 问题：addGroup, removeGroup, addStock, removeStock 等操作未返回成功/失败状态，UI 无法反馈
- 修复：让这些 async 函数返回 boolean（成功 true / 失败 false），catch 块中返回 false
- 注意：同时检查调用这些函数的 Vue 组件，看是否需要根据返回值显示 ElMessage

## 任务 2：Review Store loading 状态重构
- 文件：frontend/src/stores/review.ts
- 问题：createReview, saveNotes, removeReview 共用一个 loading state，并发操作会互相干扰
- 修复：
  1. 拆分为 creating, saving, removing 三个独立 loading ref
  2. 各函数使用自己的 loading 标记
  3. 对外暴露一个 computed loading = creating || saving || removing（兼容现有 UI）

## 任务 3：Dashboard Store 错误处理改进
- 文件：frontend/src/stores/dashboard.ts
- 问题：Promise.allSettled 后，如果 overview 失败且已有其他错误，不会覆盖 error.value
- 修复：收集所有失败的错误信息，用逗号拼接后赋给 error.value

## 验证
cd frontend && pnpm type-check && pnpm build
```

---

### Prompt 2-2：类型安全与空值防护

```
你在 stock-assistant 项目中工作。修复前端类型安全问题：

## 任务 1：SentimentView 消除 any 类型
- 文件：frontend/src/views/SentimentView.vue
- 问题：多处使用 Record<string, any>，破坏 TypeScript 类型安全
- 修复：
  1. 检查 frontend/src/types/ 下是否有 sentiment 相关类型定义
  2. 如果没有，新建 frontend/src/types/sentiment.ts，定义具体接口
  3. 把 SentimentView.vue 中所有 Record<string, any> 替换为具体类型
  4. formatMetricValue 等函数的参数也改为具体类型

## 任务 2：PositionView 空值防护
- 文件：frontend/src/views/PositionView.vue（约第 203-210 行）
- 问题：position.unrealized_pnl 和 position.realized_pnl 可能为 null/undefined，直接调 .toFixed(2) 会崩
- 修复：加空值检查，如 (position.unrealized_pnl ?? 0).toFixed(2)

## 任务 3：Plan 类型定义一致性
- 文件：frontend/src/types/plan.ts
- 问题：TradingPlan 中 risk_comment 是 string | null，但 PlanCreateData 中是可选 string（不含 null）
- 修复：统一为 string | null

## 验证
cd frontend && pnpm type-check && pnpm build
```

---

### Prompt 2-3：前端细节修复

```
你在 stock-assistant 项目中工作。修复前端细节问题：

## 任务 1：搜索防抖 timer 清理
- 文件：frontend/src/views/WatchlistView.vue（约第 54-68 行）
- 问题：searchTimer 在组件卸载时未清理，可能内存泄漏
- 修复：在 onUnmounted 钩子中 clearTimeout(searchTimer)

## 任务 2：WatchlistView parseInt 安全
- 文件：frontend/src/views/WatchlistView.vue（约第 42-51 行）
- 问题：watch(activeTab) 中 parseInt(tab) 可能返回 NaN
- 修复：parseInt 结果检查 Number.isNaN，如果是 NaN 则 fallback 到 null

## 任务 3：Sentiment Store 硬编码常量提取
- 文件：frontend/src/stores/sentiment.ts
- 问题：currentDays = ref(120) 硬编码
- 修复：在文件顶部定义 const DEFAULT_SENTIMENT_DAYS = 120，然后 ref(DEFAULT_SENTIMENT_DAYS)

## 任务 4：PlanGenerateStore parseFloat 修复
- 文件：frontend/src/stores/planGenerate.ts（约第 65 行）
- 问题：Number.parseFloat(res.data.value) || 0 在值为 0 时语义不清
- 修复：改为 Number.parseFloat(res.data.value) ?? 0（仅在 NaN/null/undefined 时 fallback）
- 注意：parseFloat 返回 NaN 而非 null，所以需要先检查：const parsed = Number.parseFloat(res.data.value); totalCapital.value = Number.isNaN(parsed) ? 0 : parsed

## 验证
cd frontend && pnpm type-check && pnpm build
```

---

## Phase 3：回归验证（依赖 Phase 1 + 2 完成）

### Prompt 3-1：全量回归 + 提交

```
你在 stock-assistant 项目中工作。执行全量回归验证：

## 步骤 1：后端全量测试
cd backend && uv run pytest tests/ -v
- 如果有失败，分析原因并修复
- 确保 216+ 个测试全部通过

## 步骤 2：前端验证
cd frontend && pnpm type-check && pnpm build
- 如果类型检查或构建失败，分析原因并修复

## 步骤 3：检查 health 端点
- 确认 backend/app/main.py 中 health 端点返回 version: "8.0.0"

## 步骤 4：提交
- git add 所有修改的文件
- 提交消息：fix: 修复V8代码审查遗留问题（事务安全、类型安全、错误处理）
- 不要推送到远程
```

---

## 问题总览

| Phase | 任务 | 问题数 | 优先级 |
|-------|------|--------|--------|
| 1-1 | 数据同步事务与锁 | 3 | P0 |
| 1-2 | 重复定义与日志统一 | 3 | P1 |
| 1-3 | 唯一约束 + API + CORS | 3 | P1 |
| 1-4 | 指标边界 + 配置矛盾 | 3 | P1 |
| 1-5 | 文档更新 | 2 | P2 |
| 2-1 | Store 错误处理 | 3 | P1 |
| 2-2 | 类型安全与空值 | 3 | P1 |
| 2-3 | 前端细节修复 | 4 | P2 |
| 3-1 | 全量回归 | 1 | P0 |
| **合计** | | **25** | |

### 并行策略

```
Phase 1（后端）──┐
                 ├──→ Phase 3（回归验证）
Phase 2（前端）──┘

Phase 1 内部：
  1-1 → 1-2 → 1-3 可串行（都改后端服务层，避免冲突）
  1-4 可与 1-1 并行（改不同文件）
  1-5 最后执行（依赖 1-1 的改动确认文档内容）

Phase 2 内部：
  2-1、2-2、2-3 可并行（改不同文件）
```
