# V8 Codex 执行提示词

本文件包含交给 Codex 的分阶段提示词。每个提示词设计为一个独立子代理任务。
Codex 应默认使用子代理模式执行，Phase 内标记为"可并行"的任务可同时启动。

> **使用方式**：把每个 `### Prompt` 块的内容直接粘贴给 Codex 作为任务描述。

---

## 给 Codex 的全局指令

```
## 项目信息
- 项目路径：stock-assistant（当前工作目录）
- 技术栈：Python FastAPI + SQLAlchemy + SQLite（后端）
- 后端包管理：uv，运行测试：cd backend && uv run pytest tests/ -v
- 当前分支：codex/v8

## 必读文件（每个任务开始前）
1. CLAUDE.md — 项目规则、架构约定、Token 规则
2. docs/V8_架构设计与开发计划.md — V8 完整设计

## 代码风格
- Python 3.12+，type hints，SQLAlchemy 2.0 ORM
- 错误响应统一使用 app/errors.py 的 build_error() 和 raise_service_error()
- Tushare token 从 config 显式传入：tushare.pro_api(TUSHARE_TOKEN)，不依赖环境变量
- 不要添加不必要的注释、docstring 到你没改的代码
- 不要引入新依赖（当前已有 pandas、tushare、sqlalchemy 等足够用）

## 子代理使用策略
- Phase A: 单独执行
- Phase B: B1 完成后执行 B2（B2 依赖 B1 的模型）
- Phase C: 可与 Phase B 并行（纯计算，不依赖模型）
- Phase D: 依赖 B + C 完成
- Phase E: 依赖 D 完成
- Phase F: 最后执行
- 每个任务完成后都要运行验证命令
- 如果测试失败，在当前子代理内修复
```

---

## Phase A：准备工作

### Prompt A1：创建分支 + 版本号

```
你在 stock-assistant 项目中工作。请完成 V8 版本管理准备：

1. 确认当前在 codex/v7 分支且工作区干净
2. 如果 v7.0 标签不存在，打标签：git tag v7.0
3. 创建新分支：git checkout -b codex/v8
4. 更新后端版本号：在 backend/app/main.py 中找到 health 端点的 version 字段，改为 "8.0.0"
5. 提交：git commit -m "chore: V8 版本管理准备"

注意：不要改其他文件，不要推送到远程。
```

---

## Phase B：数据模型 + 迁移（顺序执行 B1 → B2）

### Prompt B1：新增数据模型

```
你在 stock-assistant 项目中工作，正在开发 V8（数据库全面升级）。

请先阅读 docs/V8_架构设计与开发计划.md 第 2 节了解数据模型设计，以及 CLAUDE.md 了解项目规则。
同时阅读 backend/app/models/ 目录下的现有模型文件了解代码模式。

### 任务：创建新模型 + 重建财务模型

1. **新建 backend/app/models/indicator.py**
   - 定义 DailyIndicator 模型
   - 主键：(ts_code, trade_date)
   - 22 个 Float 字段，全部 nullable=True
   - 字段清单见设计文档 §2.1
   - 索引：ix_indicator_trade_date on trade_date

2. **新建 backend/app/models/moneyflow.py**
   - 定义 DailyMoneyflow 模型
   - 主键：(ts_code, trade_date)
   - 5 个 Float 字段：net_mf_amount, net_mf_vol, net_amount, buy_elg_amount, buy_lg_amount
   - 索引：ix_moneyflow_trade_date on trade_date

3. **新建 backend/app/models/top_list.py**
   - 定义 TopList 模型：自增 id 主键，ts_code + trade_date 有索引
   - 定义 TopListDetail 模型：自增 id 主键，ts_code + trade_date 有索引
   - 字段清单见设计文档 §2.3 和 §2.4

4. **重写 backend/app/models/financial.py**
   - 先阅读当前 financial.py 了解现有结构
   - 用设计文档 §2.5 的完整字段列表替换，保留原有的主键结构 (ts_code, ann_date, end_date)
   - 保留原有索引
   - 新增约 80 个 Float nullable 字段
   - 确保 profit_dedt 和 revenue 字段仍然存在（向后兼容 profit_growth 筛选条件）

5. **更新 backend/app/models/__init__.py**
   - 导入并导出：DailyIndicator, DailyMoneyflow, TopList, TopListDetail
   - 确保 StockFinancial 仍正常导出（重写后）

验证：cd backend && uv run pytest tests/ -v 全部通过。
```

---

### Prompt B2：Alembic 迁移

```
你在 stock-assistant 项目中工作，V8 数据模型已创建完毕。

请先阅读 backend/alembic/versions/ 目录下的现有迁移文件了解迁移模式。
特别参考 c7d8e9f0a1b2_v6_trade_and_position.py 的写法。

### 任务：创建 V8 迁移脚本

新建 backend/alembic/versions/e9f0a1b2c3d4_v8_database_upgrade.py，内容：

upgrade():
1. 创建 daily_indicator 表（从 DailyIndicator 模型）
2. 创建 daily_moneyflow 表（从 DailyMoneyflow 模型）
3. 创建 top_list 表（从 TopList 模型）
4. 创建 top_list_detail 表（从 TopListDetail 模型）
5. 删除旧 stock_financial 表
6. 用新结构重建 stock_financial 表（全字段）

downgrade():
1. 删除 daily_indicator 表
2. 删除 daily_moneyflow 表
3. 删除 top_list 表
4. 删除 top_list_detail 表
5. 删除新 stock_financial 表
6. 用旧结构（只有 ts_code, ann_date, end_date, profit_dedt, revenue, updated_at）重建 stock_financial

注意：
- revision ID 使用 "e9f0a1b2c3d4"
- down_revision 指向最新的现有迁移（读 alembic/versions/ 确认）
- 用 op.create_table() 和 op.drop_table()
- stock_financial 的处理是"删旧建新"，不是 alter

验证：cd backend && uv run pytest tests/ -v 全部通过。
同时验证：cd backend && uv run alembic heads 只显示一个 head。
```

---

## Phase C：指标计算引擎（可与 Phase B 并行）

### Prompt C1：指标计算函数

```
你在 stock-assistant 项目中工作，正在开发 V8。

请先阅读 docs/V8_架构设计与开发计划.md 第 3 节了解指标计算公式。
同时阅读 backend/app/services/indicators.py 了解现有的指标计算模式（calc_ma, calc_price_stats）。

### 任务：创建指标计算引擎

新建 backend/app/services/indicator_calc.py，实现以下函数：

#### 基础工具函数

calc_ema(values: list[float], period: int, prev_ema: float | None = None) -> float | None
- 指数移动平均
- prev_ema 为 None 时，初始值 = values[0]
- 公式：EMA = prev * (period-1)/(period+1) + current * 2/(period+1)

#### MA 系列

calc_ma_series(closes: list[float], periods: list[int]) -> dict[int, float | None]
- 一次性计算多个周期的 SMA
- 数据不足对应周期时返回 None
- periods 默认 [5, 10, 20, 60, 120, 240]

#### MACD (12, 26, 9)

calc_macd(close: float, prev_ema_fast: float | None, prev_ema_slow: float | None, prev_dea: float | None) -> dict
- 输入当日收盘价 + 前一天的 EMA_fast, EMA_slow, DEA
- 前值为 None 时使用 close 作为初始值
- 返回：{"ema_fast": ..., "ema_slow": ..., "dif": ..., "dea": ..., "hist": ...}
- hist = (dif - dea) * 2

#### KDJ (9, 3, 3)

calc_kdj(close: float, high_9: float, low_9: float, prev_k: float | None, prev_d: float | None) -> dict
- high_9 = 最近9天最高价，low_9 = 最近9天最低价
- prev_k/prev_d 为 None 时初始值 = 50
- RSV = (close - low_9) / (high_9 - low_9) * 100（分母为0时 RSV=50）
- K = prev_k * 2/3 + RSV * 1/3
- D = prev_d * 2/3 + K * 1/3
- J = 3*K - 2*D
- 返回：{"k": ..., "d": ..., "j": ...}

#### RSI (6, 12, 24)

calc_rsi(change: float, prev_avg_gain: float | None, prev_avg_loss: float | None, period: int) -> dict
- change = close - prev_close
- gain = max(change, 0), loss = max(-change, 0)
- Wilder 平滑：avg_gain = prev * (N-1)/N + gain * 1/N
- prev 为 None 时：avg_gain = gain, avg_loss = loss
- RS = avg_gain / avg_loss（avg_loss == 0 时 RSI = 100）
- RSI = 100 - 100 / (1 + RS)
- 返回：{"rsi": ..., "avg_gain": ..., "avg_loss": ...}

#### 布林带 (20, 2)

calc_boll(closes_20: list[float]) -> dict[str, float | None]
- 数据不足 20 个时返回全 None
- mid = mean(closes_20)
- std = 标准差(closes_20)
- upper = mid + 2 * std, lower = mid - 2 * std
- 返回：{"upper": ..., "mid": ..., "lower": ...}

#### ATR (14)

calc_atr(high: float, low: float, prev_close: float, prev_atr: float | None) -> dict
- TR = max(high - low, abs(high - prev_close), abs(low - prev_close))
- prev_atr 为 None 时：ATR = TR
- 否则：ATR = prev_atr * 13/14 + TR * 1/14
- 返回：{"tr": ..., "atr": ...}

#### OBV

calc_obv(close: float, prev_close: float, vol: float, prev_obv: float | None) -> float
- prev_obv 为 None 时初始 OBV = 0
- close > prev_close: OBV = prev_obv + vol
- close < prev_close: OBV = prev_obv - vol
- 相等: OBV = prev_obv

#### 量比 / 换手率变化

calc_volume_ratio(today_vol: float, recent_vols: list[float]) -> float | None
- 5日均量为 0 或列表为空时返回 None
- 返回 today_vol / mean(recent_vols)

calc_turnover_change(today_rate: float, recent_rates: list[float]) -> float | None
- 同上逻辑

#### 主入口函数

calculate_stock_indicators(
    quotes: list[dict],           # 按时间升序的行情列表，每项含 close/high/low/vol/turnover_rate
    prev_state: dict | None = None  # 前一天的累积状态（EMA值、K/D值等）
) -> list[dict]
- 遍历 quotes，逐日计算全部指标
- 返回每日的指标值 dict 列表（与 DailyIndicator 字段对应）
- 同时返回最新的累积状态（用于下次增量计算）

### 测试

新建 backend/tests/test_v8_indicators.py，覆盖：
- calc_ma_series：正常、数据不足、空列表
- calc_macd：多日连续计算，验证 DIF/DEA/HIST 数值（可用通达信公开数据对照）
- calc_kdj：含分母为0的边界情况
- calc_rsi：验证 RSI 在 0-100 范围内
- calc_boll：正常、数据不足
- calc_atr：首日 + 后续日
- calc_obv：涨跌平三种情况
- calc_volume_ratio：正常、均量为0
- calculate_stock_indicators：5-10 天的完整序列，验证输出字段完整

验证：cd backend && uv run pytest tests/test_v8_indicators.py -v 全部通过。
```

---

## Phase D：同步扩展（依赖 B + C 完成）

> Phase D 的 D1-D3 可并行执行（互不依赖），D4 依赖 D1-D3 完成。

### Prompt D1：资金流向同步

```
你在 stock-assistant 项目中工作，V8 模型已创建完毕。

请先阅读：
- docs/V8_架构设计与开发计划.md §4 了解同步流程
- backend/app/services/data_sync.py 了解现有同步模式（sync_daily_quotes 的写法）
- backend/app/models/moneyflow.py 了解模型字段
- backend/app/config.py 了解配置读取方式

### 任务：创建资金流向同步服务

新建 backend/app/services/sync_moneyflow.py：

sync_moneyflow_daily(db, trade_dates: list[str]) -> dict:
- 遍历 trade_dates，每个日期调用 Tushare moneyflow 接口
- 参数：pro.moneyflow(trade_date=date, fields="ts_code,trade_date,net_mf_amount,net_mf_vol,buy_elg_amount,buy_lg_amount,sell_elg_amount,sell_lg_amount,buy_sm_amount,sell_sm_amount,buy_md_amount,sell_md_amount")
- 计算 net_amount = (buy_sm + buy_md + buy_lg + buy_elg) - (sell_sm + sell_md + sell_lg + sell_elg)
- 只取需要的 5 个字段存入 daily_moneyflow
- 每个日期先删后插（与 sync_daily_quotes 同模式）
- sleep(BACKFILL_SLEEP) 在每次 API 调用之间
- 返回：{"synced_dates": N, "total_rows": M}

backfill_moneyflow(db, start_date: str = "20150101") -> dict:
- 检查 daily_moneyflow 表中已有的最新 trade_date
- 从断点继续，调用 sync_moneyflow_daily 逐日拉取
- 需要先获取交易日列表（从 daily_quote 表查 distinct trade_date）
- 每 20 天打印一次进度
- 返回统计信息

注意：
- Tushare token 使用 from app.config import TUSHARE_TOKEN，然后 pro = ts.pro_api(TUSHARE_TOKEN)
- 不要用 ts.pro_api() 无参调用（禁止依赖环境变量）

验证：cd backend && uv run pytest tests/ -v 不报错（此阶段无专用测试也可）。
```

---

### Prompt D2：龙虎榜同步

```
你在 stock-assistant 项目中工作，V8 模型已创建完毕。

请先阅读：
- docs/V8_架构设计与开发计划.md §2.3、§2.4、§4
- backend/app/models/top_list.py
- backend/app/services/data_sync.py（参考同步模式）

### 任务：创建龙虎榜同步服务

新建 backend/app/services/sync_toplist.py：

sync_toplist_daily(db, trade_dates: list[str]) -> dict:
- 遍历 trade_dates，每个日期调用两个 Tushare 接口：
  1. pro.top_list(trade_date=date) → 存入 top_list 表
  2. pro.top_inst(trade_date=date) → 存入 top_list_detail 表
- 每个日期先删除该日期的旧记录，再批量插入
- sleep(BACKFILL_SLEEP) 在每次 API 调用之间
- 龙虎榜不是每天都有数据，空结果跳过不报错
- 返回：{"synced_dates": N, "top_list_rows": M, "detail_rows": K}

backfill_toplist(db, start_date: str = "20150101") -> dict:
- 检查 top_list 表中已有的最新 trade_date
- 从断点继续
- 获取交易日列表（从 daily_quote 查 distinct trade_date >= start_date）
- 每 20 天打印进度
- 返回统计信息

注意：
- top_list 用自增 ID，不能用 merge/upsert，必须先 DELETE WHERE trade_date=X 再 INSERT
- Tushare token 显式传参

验证：cd backend && uv run pytest tests/ -v 不报错。
```

---

### Prompt D3：财务数据全字段拉取

```
你在 stock-assistant 项目中工作，V8 模型已创建完毕。

请先阅读：
- docs/V8_架构设计与开发计划.md §2.5
- backend/app/models/financial.py（新的全字段模型）
- backend/app/services/data_sync.py 中的 sync_financial_data()（现有逻辑）

### 任务：修改财务数据同步以支持全字段

修改 backend/app/services/data_sync.py 中的 sync_financial_data() 函数：

1. 修改 Tushare API 调用的 fields 参数，从只取 "ts_code,ann_date,end_date,profit_dedt,revenue" 改为取全部字段。
   - 不要显式列出 80 个字段名，直接不传 fields 参数（Tushare 默认返回全部）
   - 或者传 fields=""

2. 修改数据映射逻辑：
   - 现有代码手动映射 5 个字段到 StockFinancial 对象
   - 改为动态映射：遍历 DataFrame 的列，用 setattr 设置到 StockFinancial 上
   - 只映射 StockFinancial 模型中实际存在的列（用 StockFinancial.__table__.columns.keys() 做交集）

3. 保留现有的过滤逻辑：
   - 只取年报（end_date 以 "1231" 结尾）
   - 按 ann_date 降序去重
   - 只插入不存在的记录

4. 添加 backfill_financial(db) 函数：
   - 删除 stock_financial 表中所有数据
   - 遍历所有 stock_basic 记录，逐个拉取 fina_indicator
   - sleep(0.25) 每次调用之间
   - 每 100 只股票 commit 一次 + 打印进度

注意：Tushare token 显式传参。

验证：cd backend && uv run pytest tests/ -v 全部通过。
特别确保 profit_growth 筛选条件的测试仍然通过（依赖 profit_dedt 字段）。
```

---

### Prompt D4：同步流程集成 + 指标计算入库

```
你在 stock-assistant 项目中工作，V8 的同步模块（D1-D3）和指标计算引擎（C1）已完成。

请先阅读：
- docs/V8_架构设计与开发计划.md §4
- backend/app/services/indicator_calc.py（已完成的计算引擎）
- backend/app/services/sync_moneyflow.py、sync_toplist.py（已完成的同步模块）
- backend/app/services/data_sync.py（需要修改的主同步文件）

### 任务 1：创建指标计算入库服务

新建 backend/app/services/sync_indicator.py：

sync_indicators_daily(db, trade_dates: list[str]) -> dict:
- 对每个 trade_date：
  1. 查出当天所有有行情的 ts_code
  2. 对每只股票，查询该股最近 250 天行情（用于 MA240 等长周期指标）
  3. 查询该股前一天的 DailyIndicator 记录（获取累积状态）
  4. 调用 calculate_stock_indicators() 计算当天指标
  5. 写入 daily_indicator 表（先删后插）
- 返回：{"synced_dates": N, "total_rows": M}

backfill_indicators(db, start_date: str = "20150101") -> dict:
- 获取全部需要计算的股票列表
- 对每只股票：
  1. 查询该股从 2014-01-01 起的全部行情（按日期升序）
  2. 调用 calculate_stock_indicators() 一次性算出全部历史指标
  3. 批量写入 daily_indicator 表（只写 >= start_date 的记录）
- 每 100 只股票打印一次进度
- 返回统计信息

注意：
- 回填时按股票维度处理（不是按日期），因为累积型指标需要连续序列
- 每只股票一次性处理所有历史数据，内存可控（每只约 2750 天 × 22 字段）
- 日增量时按日期维度处理（因为需要快速完成）

### 任务 2：集成到 data_sync.py

修改 backend/app/services/data_sync.py：

1. 修改 sync_daily() 函数，在原有步骤后追加：
   ```python
   # V8: 新增同步
   from app.services.sync_moneyflow import sync_moneyflow_daily
   from app.services.sync_toplist import sync_toplist_daily
   from app.services.sync_indicator import sync_indicators_daily

   sync_moneyflow_daily(db, trade_dates)
   sync_toplist_daily(db, trade_dates)
   sync_indicators_daily(db, trade_dates)
   ```

2. 修改配置相关：
   - 在 backend/app/config.py 中新增：
     ```python
     HISTORY_START_DATE = settings.get("data.history_start_date", "20140101")
     BACKFILL_SLEEP = settings.get("data.backfill_sleep", 0.35)
     ```
   - 在 config/default.toml 的 [data] 段新增：
     ```toml
     history_start_date = "20140101"
     backfill_sleep = 0.35
     ```

3. 修改 run_full_sync() 中的日期范围逻辑：
   - 将基于 HISTORY_YEARS 的计算改为基于 HISTORY_START_DATE
   - 从 start_date 到今天生成交易日范围

验证：cd backend && uv run pytest tests/ -v 全部通过。
```

---

## Phase E：历史回填（依赖 D 完成）

### Prompt E1：回填调度器

```
你在 stock-assistant 项目中工作，V8 所有同步模块已完成。

请先阅读：
- docs/V8_架构设计与开发计划.md §4.2
- backend/app/services/sync_moneyflow.py 的 backfill_moneyflow()
- backend/app/services/sync_toplist.py 的 backfill_toplist()
- backend/app/services/sync_indicator.py 的 backfill_indicators()
- backend/app/services/data_sync.py 的 run_full_sync()（现有全量同步）

### 任务：创建回填调度器

新建 backend/app/services/backfill.py：

backfill_all(db) -> dict:
- 按顺序执行 5 个回填步骤，每步记录耗时：
  1. 回填 daily_quote（调用现有 run_full_sync 逻辑，但使用 HISTORY_START_DATE）
  2. 回填 daily_moneyflow（调用 backfill_moneyflow）
  3. 回填 top_list + top_list_detail（调用 backfill_toplist）
  4. 回填 stock_financial（调用 backfill_financial）
  5. 回填 daily_indicator（调用 backfill_indicators）
- 每步开始和结束都打印带时间戳的日志
- 返回每步的统计信息汇总

同时在 backend/app/api/data.py 中新增一个 API 端点用于触发回填：
POST /api/data/backfill/trigger
- 异步触发 backfill_all（在后台线程运行）
- 返回 {"status": "started"}
- 复用现有 sync_lock 防止并发

### 测试

新建 backend/tests/test_v8_sync.py：
- 测试各 backfill 函数在空数据库上不报错
- 测试 sync_indicators_daily 能正确计算并存入 daily_indicator
- 测试 sync 流程中新步骤不影响旧测试

新建 backend/tests/test_v8_models.py：
- 测试 DailyIndicator 表创建和 CRUD
- 测试 DailyMoneyflow 表创建和 CRUD
- 测试 TopList + TopListDetail 表创建和 CRUD
- 测试新 StockFinancial 表全字段 CRUD

验证：cd backend && uv run pytest tests/ -v 全部通过（含 V1-V7 旧测试）。
```

---

## Phase F：集成验证

### Prompt F1：集成联调与文档

```
你在 stock-assistant 项目中工作，V8 全部功能已开发完成。

### 步骤 1：全量测试

运行以下命令并确保全部通过：
cd backend && uv run pytest tests/ -v

如果有失败，修复后重新运行，直到全部通过。

### 步骤 2：更新 CLAUDE.md

1. 当前主开发版本改为 V8
2. 当前建议开发分支改为 codex/v8
3. 在文档入口添加 V8 文档链接
4. 新增 V8 相关约定：
   - daily_indicator 表说明
   - daily_moneyflow 表说明
   - top_list / top_list_detail 表说明
   - stock_financial 全字段说明
   - 指标计算参数：MA(5,10,20,60,120,240), MACD(12,26,9), KDJ(9,3,3), RSI(6,12,24), BOLL(20,2), ATR(14)
   - 同步流程变更：sync_daily() 新增 3 步（资金流向→龙虎榜→指标计算）
   - 配置变更：history_start_date, backfill_sleep
5. 更新最低验收标准

### 步骤 3：更新 docs/README.md

添加 V8 文档区块，将 V7 文档移到历史版本区。

### 步骤 4：验证清单

逐项确认：
- [ ] GET /api/health 返回 version 8.0.0
- [ ] daily_indicator 表结构正确（22 个指标字段）
- [ ] daily_moneyflow 表结构正确（5 个字段）
- [ ] top_list 表结构正确
- [ ] top_list_detail 表结构正确
- [ ] stock_financial 表已重建为全字段（>= 50 列）
- [ ] sync_daily() 包含资金流向、龙虎榜、指标计算步骤
- [ ] POST /api/data/backfill/trigger 端点存在
- [ ] config/default.toml 包含 history_start_date 和 backfill_sleep
- [ ] profit_growth 筛选条件测试通过（stock_financial 向后兼容）
- [ ] V1-V7 旧测试全部通过
- [ ] V8 新测试全部通过

### 步骤 5：提交

git add -A
git commit -m "feat: V8 数据库全面升级 — 技术指标/资金流向/龙虎榜/财务全字段/历史回填"
```
