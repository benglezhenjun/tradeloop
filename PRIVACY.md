# 隐私与数据流向 / Privacy & Data Flow

本系统**完全本地运行**，数据存于本机 SQLite。仅以下两种情况会向外部发送数据：

## 1. 拉取行情（Tushare）
- 同步/回填时，向 Tushare API 发送你的 token 与请求参数，拉取公开行情数据。

## 2. AI 分析（你配置的大模型服务）
当你使用 AI 功能时，应用会把相关数据发送给你在 `config/local.toml` 配置的 **OpenAI 兼容服务**（默认 DeepSeek `https://api.deepseek.com`）：

| AI 功能 | 发送的数据（摘要） |
|---|---|
| 每日研报 | 当日大盘统计、行业涨跌、你的自选股近 5 日行情、最近一次筛选结果 |
| 个股分析 | 该股近 60 日走势统计、近 3 年年报财务 |
| 交易计划 | 该股行情/财务、市场环境、**你设置的总资金** |
| 交易复盘 | **你的交易记录（价格/数量/费用）、计划、持仓期行情、总资金** |
| 行为模式 | 你多次复盘的评分汇总 |

> 即：复盘/计划类功能会把你的**资金、持仓、交易明细**发给大模型服务。请知悉。

## 如何控制
- **不配置 `api_key`** → 所有 AI 功能不可用，应用其余部分正常，不会外发任何分析数据。
- **改用本地模型**（如 Ollama / LM Studio，OpenAI 兼容）→ 把 `base_url` 指向本地，数据不出本机。
- 除上述 Tushare 与你指定的 LLM 外，本系统不向任何第三方发送数据。

## 密钥存放
Tushare token 与 LLM api_key 可在 **设置页填写**，保存在本机数据库 `data/stock.db`（已 gitignore，绝不入库），页面仅显示打码值；也可继续写在 `config/local.toml`。两者皆不随仓库分发，随仓 `data/sample.db` 为合成库、不含任何真实密钥。

---

# Privacy & Data Flow (English)

The system runs locally with SQLite. Data leaves your machine only when (1) fetching
quotes from Tushare, or (2) using AI features, which send the relevant context — including,
for review/plan features, **your capital, positions and trade details** — to the
OpenAI-compatible LLM you configure in `config/local.toml` (DeepSeek by default). To keep
everything local, point `base_url` at a local model (e.g. Ollama); leaving `api_key` unset
disables AI features entirely. No data is sent to any other third party.
