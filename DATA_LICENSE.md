# 数据使用说明 / Data Notice

本项目代码以 MIT 许可开源，但**数据不在 MIT 覆盖范围内**。

## 行情与基本面数据来源
- 真实 A 股行情、财务、资金流、龙虎榜等数据来自 [Tushare](https://tushare.pro)。
- 按 Tushare 服务协议，其数据面向**个人使用**，**不可转让、不可商业化再分发**，且**仅供参考**。
- 因此本仓库**不附带任何真实 Tushare 数据**。

## 仓库内的样例数据
- `data/sample.db` 为**程序合成的虚构数据**（随机游走生成，不对应任何真实股票/真实行情），仅用于演示界面与功能，**不可用于任何投资判断**。

## 如何获取真实数据
- 自行在 [tushare.pro](https://tushare.pro) 注册并获取 token，填入 `config/local.toml`，用 `scripts/seed_demo.py` 或完整同步流程在**本地**拉取。
- 你自行拉取的真实数据仅供你个人本地使用，请遵守 Tushare 的服务协议。

---

# Data Notice (English)

The source code is MIT-licensed, but **data is not**.

Real A-share market/financial data comes from [Tushare](https://tushare.pro) and, under
its terms, is for **personal, non-transferable, non-commercial, reference-only** use.
This repository therefore ships **no real Tushare data**. The bundled `data/sample.db`
is **synthetic, fictional data** for demo only and must not be used for any investment
decision. To use real data, register your own Tushare token and fetch locally.
