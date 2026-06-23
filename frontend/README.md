# TradeLoop · 前端

Vue 3 + TypeScript + Pinia + Element Plus + ECharts + Vite。

## 环境
- Node ≥ 20.19
- [pnpm](https://pnpm.io) 10

## 快速开始
```bash
cd frontend
pnpm install
pnpm dev          # 开发服务器（默认 http://localhost:5173）
```

## 配置
- 后端地址通过环境变量 `VITE_API_URL` 读取，开发默认 `http://localhost:8000`。
- 可在 `frontend/.env.development` 覆盖。

## 常用命令
```bash
pnpm type-check   # 类型检查
pnpm build        # 生产构建
pnpm lint         # 代码检查（本地，带自动修复）
```
