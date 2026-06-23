# V8 Code Review — 问题清单

> 审查时间：2026-04-07
> 审查范围：V8 全部后端代码（模型、迁移、服务、API、测试）+ 前端
> 总结：数据模型和迁移质量优秀，backfill 已成功完成。主要问题集中在 **服务层的计算逻辑、线程安全、错误处理**。

---

## 一、严重（CRITICAL）— 必须修复

### C1. indicator_calc.py — ATR/OBV 首行计算使用了错误的 prev_close ✅

**文件**: `backend/app/services/indicator_calc.py` 约第 250-253 行
**问题**: 当 `prev_close is None` 时，代码用当前 `close` 代替，导致：
- ATR 首行忽略了跳空缺口逻辑
- OBV 首行比较 close vs close，永远判为平盘（OBV 不变）

**修复建议**: prev_close 为 None 时，ATR 和 OBV 该行应返回 None，而非用 close 顶替。

---

### C2. indicator_calc.py — volume_ratio 在 append 之前计算 ✅

**文件**: `backend/app/services/indicator_calc.py` 约第 211-217 行
**问题**: `recent_vols = vols[-5:]` 在 `vols.append(vol)` **之前**执行，导致前 5 行的 volume_ratio 始终为 None（其实可以算）。
**修复建议**: 先 append 再取 `vols[-5:]`。

---

### C3. sync_indicator.py — zip(strict=False) 可能导致数据错位 ✅

**文件**: `backend/app/services/sync_indicator.py` 约第 85 行
**问题**: `zip(quotes, indicator_rows, strict=False)` 如果两个列表长度不一致，会静默截断，指标数据可能和日期对不上。
**修复建议**: 改为 `strict=True`，或在 zip 前加长度校验并抛异常。

---

### C4. data_sync.py — backfill_financial() 未获取 sync_lock ✅

**文件**: `backend/app/services/data_sync.py` 约第 244-278 行
**问题**: `backfill_financial()` 先 DELETE 全表再 INSERT，但没有获取 `sync_lock`。如果日常同步和 backfill 同时运行，会数据冲突。
**修复建议**: 加上 `sync_lock.acquire(blocking=False)` 保护，和其他 sync 函数一致。

---

### C5. data_sync.py — sync_daily_quotes() delete+insert 无事务保护 ✅

**文件**: `backend/app/services/data_sync.py`（sync_indicator 类似）
**问题**: 先 DELETE 某日指标，再 INSERT。如果 INSERT 失败，该日数据就丢了，没有事务回滚包裹。
**修复建议**: 用显式事务 `with db.begin()` 包裹 delete+insert。

---

## 二、高优先级（HIGH）

### H1. backfill.py — 全局状态变量无线程锁 ✅

**文件**: `backend/app/services/backfill.py` 约第 16-18 行, 73-89 行
**问题**: `_backfill_status`, `_backfill_error`, `_backfill_finished_at` 是全局变量，在后台线程写、在 API 端点读，没有加 `threading.Lock()`，可能读到不一致状态。
**修复**: 加 `_backfill_lock = threading.Lock()`，读写都加锁。

---

### H2. backfill.py — daemon 线程不等待完成 ✅

**文件**: `backend/app/services/backfill.py` 约第 97 行
**问题**: `daemon=True` 意味着主进程退出时线程直接被杀，backfill 可能中途中断而无日志。
**修复**: 改为非 daemon 线程，或保存线程引用以便优雅关闭。

---

### H3. sync_toplist.py — NaN 检测方式不规范 ✅

**文件**: `backend/app/services/sync_toplist.py` 约第 20-21 行
**问题**: 用 `value == value` 检测 NaN 是反模式，虽然结果碰巧正确但难以维护。
**修复**: 改用 `pd.notna(value)` 或 `math.isnan()`。

---

### H4. sync_moneyflow.py — 异常处理吞掉错误状态 ✅

**文件**: `backend/app/services/sync_moneyflow.py` 约第 76-79 行
**问题**: 捕获异常后只 print + sleep(2)，然后继续。调用方看到的 total_rows 包含了失败批次的部分数据，以为全部成功。
**修复**: 记录失败日期列表，返回时区分成功/失败数量。

---

### H5. main.py — 健康检查消息写的是 V7 ✅

**文件**: `backend/app/main.py` 约第 100 行
**问题**: `"message": "A股交易辅助系统 V7 运行中"` 应改为 V8。（`version` 字段已经是 `"8.0.0"` 了，message 忘改。）
**修复**: 改为 `"A股交易辅助系统 V8 运行中"`。

---

### H6. 缺少 V8 API 集成测试 ✅

**文件**: `backend/tests/` 目录
**问题**: 有 `test_v8_models.py`、`test_v8_sync.py`、`test_v8_indicators.py`、`test_v8_migration.py`，但缺少用 FastAPI TestClient 测 API 端点的文件：
- `POST /api/data/backfill/trigger`
- `GET /api/data/backfill/status`（如果有的话）
- `GET /api/dashboard/*`
- `GET /api/kline/{ts_code}`

**修复**: 新建 `test_v8_api.py`，补充端点级测试。

---

## 三、中等优先级（MEDIUM）

### M1. data_sync.py — 函数内部延迟 import 有循环引用风险 ✅

**文件**: `backend/app/services/data_sync.py` 约第 289-291 行
**问题**: `sync_daily()` 里在函数体内 import 其他模块，可能有循环依赖。
**修复**: 尽量提到模块顶部。

---

### M2. dashboard.py — 重复定义 get_db() ✅

**文件**: `backend/app/api/dashboard.py` 约第 17-22 行
**问题**: 自己定义了 `get_db()`，但 `app.database` 已经导出了同名函数。
**修复**: 改为 `from app.database import get_db`。

---

### M3. data_sync.py — backfill_financial() 硬编码 sleep(0.25) ✅

**文件**: `backend/app/services/data_sync.py` 约第 257 行
**问题**: 其他函数用 `BACKFILL_SLEEP`（0.35s），这里硬编码 0.25。
**修复**: 统一使用配置常量。

---

### M4. sync_indicator.py — sync_indicators_daily() 缺少 per-stock 错误处理 ✅

**文件**: `backend/app/services/sync_indicator.py` 约第 21-66 行
**问题**: 如果某只股票的 `calculate_stock_indicators()` 抛异常，整批失败。
**修复**: 加 try-except 跳过单只股票的错误，记录日志。

---

### M5. data_sync.py — session 管理不一致 ✅

**文件**: `backend/app/services/data_sync.py` 多处
**问题**: 有的函数用 `SessionLocal()` + try-finally，有的不关闭，203-210 行同一操作打开了两次 DB。
**修复**: 统一用 context manager 或 try-finally。

---

### M6. scheduler.py — 定时任务无异常捕获 ✅

**文件**: `backend/app/services/scheduler.py` 约第 16-24 行
**问题**: `_daily_sync_job()` 没有 try-except，如果 `try_start_sync()` 抛异常，调度器可能静默失败。
**修复**: 加 try-except + logging.error。

---

### M7. API 响应格式不统一

**位置**: `api/data.py`, `api/screening.py` 等多个文件
**问题**: 有的返回 `{"status": "started"}`，有的返回裸数据，有的带 `{"error": ...}`。没有统一的响应信封格式。
**建议**: 可在后续版本统一，当前不阻塞。

---

## 四、低优先级（LOW）

### L1. 前端缺少 backfill API 函数

**文件**: `frontend/src/api/index.ts`
**问题**: 后端有 `POST /api/data/backfill/trigger`，前端 API 客户端没有对应函数。
**说明**: V8 规范说不改前端，但如果未来要在设置页触发 backfill 就需要。可先补上函数不调用。

---

### L2. TopList 缺少数据库层唯一约束 ✅

**文件**: `backend/app/models/top_list.py`
**问题**: 仅靠 Service 层的 Python 去重逻辑防止重复，数据库层没有 `UNIQUE(ts_code, trade_date, reason)` 约束。
**建议**: 加 DB 唯一约束作为安全网。

---

### L3. DailyMoneyflow 丢弃了 sell_elg_amount / sell_lg_amount

**文件**: `backend/app/models/moneyflow.py` + `sync_moneyflow.py`
**问题**: API 返回了卖方数据但模型没存。虽然可以从 net 值反算，但未来筛选条件可能需要原始值。
**建议**: 如果未来 V9+ 需要，提前加列；如果不需要就在模型注释里说明设计决策。

---

### L4. api/__init__.py 只导出了 review ✅

**文件**: `backend/app/api/__init__.py`
**问题**: `__all__` 只有 `["review"]`，实际 main.py import 了 13 个 router。
**建议**: 补全导出，保持一致性。

---

### L5. kline.py — 先 DESC 再 reverse 的性能浪费 ✅

**文件**: `backend/app/services/kline.py` 约第 61-62 行
**问题**: 查询用 DESC 排序，拿到后又 `list(reversed(rows))`，多一次遍历。
**修复**: 直接用 ASC 排序。

---

## 五、确认无问题的部分

| 模块 | 状态 | 说明 |
|------|------|------|
| 数据模型（5 个 model 文件）| ✅ 优秀 | 字段、类型、索引全部正确，模型与迁移 100% 对齐 |
| Alembic 迁移 | ✅ 优秀 | upgrade/downgrade 对称，幂等安全 |
| models/__init__.py | ✅ | 14 个模型全部正确导入导出 |
| database.py | ✅ | 外键约束、session 工厂、依赖注入均正确 |
| 前端路由/组件/Store | ✅ | 15 个路由、11 个 store 全部正常，V8 不需要前端改动 |
| 数据 backfill 结果 | ✅ | 5 张 V8 表全部填充完毕（indicator 1112 万行、moneyflow 1080 万行、toplist 17.5 万+228 万行、financial 6.7 万行）|

---

## 六、修复优先级总结

| 级别 | 数量 | 编号 |
|------|------|------|
| 严重（必须修） | 5 | C1, C2, C3, C4, C5 |
| 高（应该修） | 6 | H1-H6 |
| 中（建议修） | 7 | M1-M7 |
| 低（可选） | 5 | L1-L5 |
| **合计** | **23** | |

建议按 C → H → M 顺序修复，L 级别可留到下个版本。
