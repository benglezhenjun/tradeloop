# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) 风格。

## [Unreleased] — 开源精品化
### 变更
- 移除 MVP 时期遗留死代码（`models.py` / `data_sync.py` / `screening.py`）。
- 重命名易混淆模块：`indicators.py` → `price_stats.py`，`indicator_calc.py` → `technical_indicators.py`。
- 调度器与事件改用 logging；删除未使用的事件总线占位。
### 修复
- 选股「均线多头排列」宽松模式不再被强制要求 240 个交易日。
- `ma_proximity` / `ma_slope` 改按交易日取窗口，长期停牌/长假个股不再被误删。
- AI 返回的截断 JSON 数组不再被静默当作单个对象。
- 持仓部分卖出改用精确比例摊销成本，消除累计舍入漂移。
### 工程
- 引入 ruff lint 门禁；新增 GitHub Actions CI（pytest / type-check / build / gitleaks）、Dependabot。
- 新增 LICENSE、数据使用说明、风险免责、隐私说明、贡献指南。

## [8.0.0] — 数据层大升级
- 新增预计算技术指标（MA/MACD/KDJ/RSI/BOLL/ATR/OBV 等，22 项）、个股资金流向、龙虎榜（汇总+明细）。
- 财务数据升级为全字段；历史数据回溯至 2014 年。

## [7.0.0] — AI 交易复盘 + 行为模式识别
- 对已清仓交易做 8 维度 AI 复盘（雷达图）；累计多笔后识别交易行为模式。

## [6.0.0] — 交易记录 + 持仓管理
- 记录买卖与自动费用计算（佣金/印花税/过户费）；持仓与盈亏自动重算。

## [5.0.0] — AI 交易计划
- AI 生成激进/稳健/保守三套交易方案，含入场/止损/分批止盈/仓位。

## [4.0.0] — AI 智能分析
- 每日研报（5 个 Agent 串联）与个股深度分析。

## [3.0.0] — 市场仪表盘
- 市场概览、行业热度、市场宽度趋势。

## [2.0.0] — 自选股管理
- 自选分组 CRUD、个股详情页、K 线图、筛选结果批量加入自选。

## [1.0.0] — 基础数据层
- Tushare 数据同步，股票基础信息与日线行情入本地 SQLite；可插拔选股策略引擎。
