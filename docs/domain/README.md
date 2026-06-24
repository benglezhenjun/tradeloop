# Domain 设计文档 · Domain Design Notes

> 用图文讲清 TradeLoop 背后的金融逻辑——不只是"能跑"，而是"为什么这么算"。
> Illustrated notes on the financial logic behind TradeLoop — not just "it runs", but "why it's computed this way".

## 篇目 · Contents

| 主题 Topic | 中文（主） | English |
|---|---|---|
| 交易闭环 · 费用与持仓规则<br/>Trade loop · fees & position rules | [trade-loop.md](./trade-loop.md) | [trade-loop.en.md](./trade-loop.en.md) |
| 选股引擎 · 插件式条件筛选<br/>Screening engine · pluggable conditions | [screening-engine.md](./screening-engine.md) | [screening-engine.en.md](./screening-engine.en.md) |

每篇都**对应真实代码**（带文件/行号引用），并尽量给出可手算复核的算例或数据流图。
Each note **maps to real code** (with file/line references) and includes hand-checkable worked examples or data-flow diagrams where possible.

> 免责声明 · Disclaimer：本系统仅为个人交易辅助与学习工具，不构成投资建议。This is a personal trading-assistant and learning tool, not investment advice. — [FINANCIAL_DISCLAIMER.md](../../FINANCIAL_DISCLAIMER.md)
