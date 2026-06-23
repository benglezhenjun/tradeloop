# V5 Verification

日期：`2026-04-06`
分支：`v5-dev`
基线：`v5.0-draft`

## 1. 后端自动化

### 命令

```powershell
cd backend
uv run pytest tests/ -v
```

### 结果

- 退出码：`0`
- 摘要：`101 passed`

### 关键覆盖

- `POST /api/plan` 返回 `201`
- `PUT / PATCH` 对不存在计划返回 `404`
- 仓位上限、止盈比例和状态流转规则
- `generate` 的 `ok / manual_fallback / 404 / 502`
- `total_capital` 默认值 `"0"`

## 2. 前端静态验证

### 命令

```powershell
cd frontend
pnpm type-check
pnpm build
```

### 结果

- `pnpm type-check`
  - 退出码：`0`
  - 结果：通过
- `pnpm build`
  - 退出码：`0`
  - 结果：通过
  - 备注：存在 Vite chunk size warning，不影响本轮 V5 验收

## 3. 交互式 Smoke

### 环境

- 临时 backend：`http://127.0.0.1:8000`
- 临时 frontend：`http://localhost:5173`
- 浏览器工具：Playwright MCP `browser_run_code`

### 3.1 设置页保存总资金

- 方式：真实 backend + 真实前端
- 步骤：
  - 打开 `/settings`
  - 在“总资金（元）”输入 `500000`
  - 点击“保存”
  - 通过 `GET /api/config/total_capital` 二次确认
- 结果：
  - 页面输入值保留为 `500000`
  - API 返回 `{"key":"total_capital","value":"500000"}`

### 3.2 `/plan` 手动创建计划

- 方式：真实 backend + 真实前端
- 步骤：
  - 打开 `/plan`
  - 点击“手动创建”
  - 搜索并选择 `000001.SZ`
  - 填写目标价 `12.34`、止损价 `11.11`、止盈 `13.50 / 1.0`
  - 填写理由 `V5 smoke manual create`
  - 点击“创建计划”
- 结果：
  - toast：`计划已创建`
  - 列表新增 `平安银行 000001.SZ`
  - 新计划状态为 `待执行`

### 3.3 `/plan` 编辑 `pending` 计划

- 方式：真实 backend + 真实前端
- 步骤：
  - 在 `/plan` 点击新建计划的“编辑”
  - 目标价改为 `12.88`
  - 理由改为 `V5 smoke edited`
  - 点击“保存修改”
- 结果：
  - toast：`计划已更新`
  - 列表中的目标价更新为 `12.88`

### 3.4 `/plan` 状态流转

- 方式：真实 backend + 真实前端
- 步骤：
  - 在 `/plan` 点击新建计划的“已执行”
  - 在确认框点击“确定”
- 结果：
  - toast：`已标记为已执行`
  - 该计划状态显示为 `已执行`
  - 该计划的“编辑”按钮消失

### 3.5 `/plan/generate/600519.SH` 成功流

- 方式：Playwright route mock
- mock：
  - `GET /api/health` -> 在线
  - `GET /api/config/total_capital` -> `500000`
  - `POST /api/plan/generate/600519.SH` -> `status: "ok"`，返回 3 套方案
  - `POST /api/plan` -> `201`
- 步骤：
  - 打开 `/plan/generate/600519.SH`
  - 确认页面展示三栏方案
  - 点击第一套“选择此方案”
  - 在共享编辑器中把目标价改为 `1699`
  - 点击“保存所选方案”
- 结果：
  - 成功进入三栏 compare 状态
  - 成功进入 editor 状态
  - toast：`交易计划已保存`
  - 跳转回 `/plan`

### 3.6 `/plan/generate/000001.SZ` manual fallback

- 方式：Playwright route mock
- mock：
  - `GET /api/health` -> 在线
  - `GET /api/config/total_capital` -> `500000`
  - `POST /api/plan/generate/000001.SZ` -> `status: "manual_fallback"`
- 步骤：
  - 打开 `/plan/generate/000001.SZ`
- 结果：
  - 页面显示 warning：`LLM 输出不可直接使用，请手动补建计划。`
  - 直接进入共享编辑器
  - 股票信息预填为 `000001.SZ / 平安银行`

### 3.7 总资金未设置时跳转设置页

- 方式：Playwright route mock
- mock：
  - `GET /api/health` -> 在线
  - `GET /api/config/total_capital` -> `"0"`
- 步骤：
  - 打开 `/plan/generate/600519.SH`
- 结果：
  - 跳转到 `/settings`
  - toast：`请先在设置页设置总资金`

## 4. 限制说明

- 交互式 smoke 中，生成页相关场景使用了前端路由 mock，目的是稳定验证页面状态机和用户流程，而不是验证现场 LLM 可用性。
- 现场 LLM/provider 的可用性仍由后端 API 测试和真实环境配置共同保证。
- 本轮没有引入正式前端 E2E 测试基础设施；如果后续版本要做长期回归，建议补充 Playwright 测试工程。
