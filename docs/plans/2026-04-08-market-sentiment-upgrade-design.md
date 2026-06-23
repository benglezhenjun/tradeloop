# 市场情绪升级设计文档

更新时间：2026-04-08
当前基线：V8（数据层升级已完成）
设计目标：在现有“看大盘 -> 选股 -> AI 分析 -> 计划 -> 交易 -> 复盘”闭环中，补齐短线情绪判断能力，并以可回填、可画历史图、可被 AI 和页面复用的方式落地。

---

## 1. 已确认的产品决策

本设计基于以下用户确认：

1. 范围不仅包含 5 个情绪指标本身，还包含：
   - 首页简版情绪卡片
   - 独立情绪页
   - AI 日报与交易计划的软联动
   - 后续策略页的软联动提示
2. 必须支持历史回填与历史走势图，不接受“仅上线后累计”。
3. 执行必须按阶段推进。
4. 任何一步没有完全通过测试、数据校验、手工验收和 Git 检查点，不允许进入下一步。
5. 策略联动先做软联动，不把情绪指标直接变成筛股硬条件。
6. 当前阶段必须受限于用户现有 Tushare 权限，原始数据源只能使用 6000 积分以内可访问接口；不得把 8000+ 权限接口作为 Phase 1 门禁依赖。

---

## 2. 目标与非目标

### 2.1 目标

本次升级要补齐以下 5 个核心指标：

1. 连板高度
2. 炸板率
3. 昨日涨停溢价
4. 高位股晋级率
5. 主线持续天数

本次升级最终要达到的效果：

1. 后端能稳定同步、回填和持久化情绪原始数据。
2. 后端能产出逐日情绪快照，供页面和 AI 统一复用。
3. 首页能展示当日关键情绪摘要。
4. 独立情绪页能展示历史走势图、分项解释、主线演化。
5. AI 日报、交易计划、筛选结果页能读取情绪数据做软联动提示。

### 2.2 非目标

本次升级明确不做：

1. 不接入券商自动下单。
2. 不把情绪指标直接加入策略条件引擎。
3. 不在本次做分时级情绪数据。
4. 不新增复杂的消息通知系统。
5. 不在第一轮做“龙头股识别引擎”或“自动主线切换策略”。

---

## 3. 数据源设计

### 3.1 必须数据源

#### A. 涨跌停明细

优先数据源：
- Tushare `limit_list_d`
- 文档参考：[https://tushare.pro/document/2?doc_id=298](https://tushare.pro/document/2?doc_id=298)

用途：
- 连板高度
- 炸板率
- 昨日涨停溢价
- 高位股晋级率

最低必需字段：
- `ts_code`
- `trade_date`
- `name`
- `limit_type`
- `limit_times`
- `up_stat`
- `first_time`
- `last_time`
- `open_num`
- `fd_amount`

说明：
- `limit_type='U'` 用于封板池
- `limit_type='Z'` 用于炸板池
- 跌停池可作为后续扩展，不作为本次 5 指标核心输入

#### B. 题材热度榜

优先数据源：
- Tushare `ths_hot`
- 文档参考：[https://tushare.pro/document/2?doc_id=320](https://tushare.pro/document/2?doc_id=320)

用途：
- 主线持续天数
- 主线演化

最低必需字段：
- `trade_date`
- `ts_code`
- `ts_name`
- `rank`
- `hot`
- `rank_reason`

说明：
- 固定使用 `market='概念板块'`
- 固定使用 `is_new='N'`，以支持历史回填
- 同一交易日按 `ts_code` 去重，优先保留 `rank_time` 最新的一条；若 `rank_time` 相同，则保留 `hot` 更高记录
- 该接口在当前 6000 积分权限内可访问，可替代 `limit_cpt_list` 作为 Phase 1 主线题材原始输入

### 3.2 可选增强数据源

增强数据源：
- Tushare `limit_list_ths`
- Tushare `ths_member`
- 文档参考：[https://tushare.pro/document/2?doc_id=355](https://tushare.pro/document/2?doc_id=355)
- 文档参考：[https://tushare.pro/document/2?doc_id=261](https://tushare.pro/document/2?doc_id=261)

用途：
- 独立情绪页增强展示
- 连板池 / 炸板池 / 冲刺涨停等更细标签

约束：
- 历史范围从 2023-11-01 开始
- 不作为第一阶段硬依赖

---

## 4. 指标口径设计

### 4.1 连板高度

定义：
- 当日封板股票中 `limit_times` 的最大值

输出字段：
- `max_limit_height`
- `max_limit_height_count`
- `max_limit_height_codes`

说明：
- 如果最高板有多只，全部记录
- 若当日无封板股，返回 `0 / 0 / []`

### 4.2 炸板率

定义：
- `炸板率 = 炸板家数 / (封板家数 + 炸板家数)`

输出字段：
- `limit_up_count`
- `limit_broken_count`
- `broken_rate`

说明：
- 分母为 0 时，炸板率定义为 `0`

### 4.3 昨日涨停溢价

V1 口径：
- 取昨日封板池股票
- 读取这些股票今日 `daily_quote.pct_chg`
- 计算平均值、中位数、红盘率

输出字段：
- `yday_limit_premium_avg`
- `yday_limit_premium_median`
- `yday_limit_red_rate`
- `yday_limit_sample_count`

说明：
- 先用收盘溢价，不做开盘溢价
- 停牌或缺失行情的样本不参与统计

### 4.4 高位股晋级率

默认高位阈值：
- `3 连板及以上`

定义：
- 昨日 `limit_times >= 3` 的股票中
- 今天继续封板，且今日 `limit_times = 昨日 limit_times + 1`
- 计为晋级成功

输出字段：
- `high_board_threshold`
- `high_board_total`
- `high_board_advanced`
- `high_board_promotion_rate`

说明：
- 高位阈值先做成后端常量和可配置参数，但前端默认显示 `3`

### 4.5 主线持续天数

定义：
- 每个交易日从 `theme_heat_daily` 中选出一个“主线主题”
- 若今日主线与昨日相同，则 `streak_days + 1`
- 若不同，则重置为 1

V1 主线主题判定规则：

1. 优先看 `rank`
2. 再看 `score`（来自 `ths_hot.hot`）
3. 同一主题若存在多次热榜快照，优先取 `rank_time` 最新的一条
4. 若同日多个主题并列，优先选热度值更高者
5. 本阶段不再依赖 `up_nums/cons_nums`

输出字段：
- `main_theme_code`
- `main_theme_name`
- `main_theme_score`
- `main_theme_streak_days`

说明：
- 本轮先保证规则稳定，不做机器学习或复杂聚类

---

## 5. 架构设计

### 5.1 新增数据表

#### `limit_event_daily`

定位：
- 逐股逐日涨停/炸板原始事件表

建议字段：
- `ts_code`
- `trade_date`
- `name`
- `limit_type`
- `limit_times`
- `up_stat`
- `first_time`
- `last_time`
- `open_num`
- `fd_amount`
- `source`

索引建议：
- `(trade_date)`
- `(ts_code, trade_date)`
- `(trade_date, limit_type)`

#### `theme_heat_daily`

定位：
- 逐主题逐日热度原始表

建议字段：
- `trade_date`
- `theme_code`
- `theme_name`
- `rank`
- `up_nums`
- `cons_nums`
- `up_stat`
- `score`
- `source`

说明：
- 在 `ths_hot` 口径下，`up_nums`、`cons_nums` 允许为空
- `up_stat` 暂存 `rank_reason`
- `score` 直接存 `hot`
- 行数验收按“去重后最终入库口径”核对，不直接使用 `ths_hot` 原始快照总行数

索引建议：
- `(trade_date)`
- `(theme_code, trade_date)`

#### `market_sentiment_daily`

定位：
- 逐日情绪快照表
- 首页、情绪页、AI、软联动统一使用

建议字段：
- `trade_date`
- `max_limit_height`
- `max_limit_height_count`
- `max_limit_height_codes_json`
- `limit_up_count`
- `limit_broken_count`
- `broken_rate`
- `yday_limit_premium_avg`
- `yday_limit_premium_median`
- `yday_limit_red_rate`
- `yday_limit_sample_count`
- `high_board_threshold`
- `high_board_total`
- `high_board_advanced`
- `high_board_promotion_rate`
- `main_theme_code`
- `main_theme_name`
- `main_theme_score`
- `main_theme_streak_days`
- `notes_json`

索引建议：
- `(trade_date)`

### 5.2 后端模块拆分

新增或修改模块：

1. 模型层
   - `backend/app/models/limit_event.py`
   - `backend/app/models/theme_heat.py`
   - `backend/app/models/market_sentiment.py`
   - `backend/app/models/__init__.py`

2. 同步层
   - `backend/app/services/sync_limit_event.py`
   - `backend/app/services/sync_theme_heat.py`
   - 修改 `backend/app/services/data_sync.py`
   - 修改 `backend/app/services/backfill.py`

3. 计算层
   - `backend/app/services/market_sentiment.py`

4. API 层
   - 新增 `backend/app/api/sentiment.py`
   - 修改 `backend/app/main.py`

5. AI 软联动层
   - 修改 `backend/app/services/agents/daily.py`
   - 修改 `backend/app/services/agents/plan.py`

### 5.3 API 设计

建议新增以下接口：

1. `GET /api/dashboard/sentiment/summary`
   - 返回最新交易日快照
   - 首页和情绪页顶部卡片共用

2. `GET /api/dashboard/sentiment/history?days=120`
   - 返回 5 个核心指标的历史序列

3. `GET /api/dashboard/sentiment/themes?days=120`
   - 返回主线主题历史

4. `GET /api/dashboard/sentiment/detail/{trade_date}`
   - 返回某日分项解释与样本股

说明：
- 不把情绪接口塞进现有 `overview` 返回值，避免接口过度膨胀

---

## 6. 前端设计

### 6.1 首页简版

目标：
- 首页只展示“最新情绪摘要”
- 不展示历史大图

展示建议：
- 连板高度
- 炸板率
- 昨日涨停溢价
- 高位股晋级率
- 主线主题 + 持续天数

涉及文件：
- `frontend/src/views/DashboardView.vue`
- `frontend/src/stores/dashboard.ts`
- `frontend/src/types/dashboard.ts`

### 6.2 独立情绪页

新增页面：
- `frontend/src/views/SentimentView.vue`

新增 store / type：
- `frontend/src/stores/sentiment.ts`
- `frontend/src/types/sentiment.ts`

展示内容：

1. 顶部摘要卡片
2. 5 个指标历史走势图
3. 分项解释卡片
4. 主线演化时间线
5. 某日代表样本股

路由与导航：
- 修改 `frontend/src/router/index.ts`
- 修改 `frontend/src/components/AppSidebar.vue`

---

## 7. AI 与软联动设计

### 7.1 AI 日报

目标：
- 在现有市场环境分析之外，新增情绪面摘要

做法：
- `run_market_agent()` 增加情绪快照输入
- LLM 只做解释，不改变原始数值

输出重点：
- 今日短线情绪偏热 / 偏冷 / 分歧
- 主线是否延续
- 高位风险是否加大

### 7.2 交易计划

目标：
- 计划生成时把市场情绪作为风险背景

做法：
- `run_plan_agent()` 增加情绪摘要文案
- 例如：
  - 炸板率高时，提示“追高风险上升”
  - 昨日涨停溢价低时，提示“接力环境偏弱”

### 7.3 页面软联动

第一轮只做提示，不做硬筛选：

1. 筛选页：显示“当前情绪摘要”
2. 计划页：显示“计划生成时的情绪背景”
3. 个股分析页：显示“所处情绪周期提示”

---

## 8. 分阶段实施策略

### 第 1 阶段：情绪原始数据底座

目标：
- 打通同步、迁移、历史回填

阶段交付：
- 新表
- 每日增量同步
- 全量回填
- 原始数据抽样校验

阶段门禁：
- 若迁移、回填、抽样任一项未通过，禁止进入第 2 阶段

### 第 2 阶段：情绪指标计算与 API

目标：
- 产出 5 个稳定指标和统一查询接口

阶段交付：
- `market_sentiment_daily`
- 计算服务
- 摘要 / 历史 / 主题 / 详情 API

阶段门禁：
- 若公式测试、样本日期复核、API 回归任一项未通过，禁止进入第 3 阶段

### 第 3 阶段：首页与独立情绪页

目标：
- 让情绪数据可视化可使用

阶段交付：
- 首页卡片
- 独立情绪页
- 历史走势图
- 主线演化

阶段门禁：
- 若类型检查、构建、手工验收任一项未通过，禁止进入第 4 阶段

### 第 4 阶段：AI 软联动

目标：
- 把情绪数据接入 AI 日报和交易计划

阶段交付：
- 情绪摘要生成
- 日报引用
- 计划风控提示

阶段门禁：
- 若 LLM 降级逻辑、提示词稳定性、回归验收任一项未通过，禁止进入第 5 阶段

### 第 5 阶段：页面软联动与总回归

目标：
- 把情绪结论接到筛选、计划、分析等页面

阶段交付：
- 软联动提示
- 文档收口
- 全链回归

阶段门禁：
- 若全链路回归未通过，本次升级不得宣告完成

---

## 9. 检验与打磨要求

本设计强制执行以下规则：

1. 先红后绿
   - 后端先写失败测试
   - 跑出真实失败
   - 再写最小实现
   - 再跑通过

2. 每阶段必须有数据抽样校验
   - 随机交易日
   - 极端情绪交易日
   - 边界交易日

3. 每阶段必须有人工验收清单
   - 不接受“我看起来没问题”
   - 必须有明确动作和预期结果

4. 每阶段必须有 Git 检查点
   - 单独提交
   - 提交信息中文、简洁、可回退

5. 明确停止条件
   - 任何阶段未通过验收，不得进入下一阶段
   - 必须先修复、复测、回归、提交，再申请进入下一阶段

---

## 10. 风险与应对

### 10.1 数据源口径差异

风险：
- Tushare 不同接口对炸板、题材的口径可能有差异

应对：
- 第一轮固定主口径，只用一套定义
- 把字段映射和口径写入测试

### 10.2 历史回填耗时

风险：
- 情绪原始数据回填需要额外网络请求与本地写库

应对：
- 与现有 `sync_lock` 复用
- 断点续传
- 阶段日志输出

### 10.3 页面复杂度上升

风险：
- 首页和情绪页很容易塞太多内容

应对：
- 首页只放摘要
- 详细图表全部放独立情绪页

### 10.4 AI 输出失真

风险：
- LLM 可能把情绪指标解释过头

应对：
- AI 只解释现成数据，不自己推导数值
- 提示词明确“不预测涨跌”

---

## 11. Git 与交付策略

建议提交粒度：

1. `feat: 新增市场情绪原始数据模型与回填`
2. `feat: 新增市场情绪快照计算与接口`
3. `feat: 新增独立情绪页与首页情绪摘要`
4. `feat: 接入情绪摘要到日报与交易计划`
5. `feat: 完成情绪软联动与全链回归`

每个提交前必须完成：
- 对应测试通过
- 对应人工验收通过
- `git status --short` 可解释

---

## 12. 最终判断标准

本次升级完成的唯一标准不是“代码写完”，而是：

1. 数据能同步
2. 历史能回填
3. 图能画出来
4. AI 能正确引用
5. 每一阶段都已通过独立验收

如果上述 5 条有任意一条未达成，本次升级都应视为“未完成”。
