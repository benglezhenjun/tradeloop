# V5 Archive Index

本目录是 V5 打磨版的细粒度归档入口，供 Claude 或人工复核直接查询：

- review finding 如何被修复
- 动了哪些文件
- 每个文件为什么动
- 验证命令和结果是什么

## 阅读顺序

1. [`docs/V5_打磨完成进度书.md`](/D:/构想/stock-assistant/docs/V5_打磨完成进度书.md)
2. [`docs/archive/V5/review_resolution.md`](/D:/构想/stock-assistant/docs/archive/V5/review_resolution.md)
3. [`docs/archive/V5/change_manifest.json`](/D:/构想/stock-assistant/docs/archive/V5/change_manifest.json)
4. [`docs/archive/V5/verification.md`](/D:/构想/stock-assistant/docs/archive/V5/verification.md)

## 文件说明

- [`docs/archive/V5/review_resolution.md`](/D:/构想/stock-assistant/docs/archive/V5/review_resolution.md)
  - review finding 编号、原问题、修复动作、状态
- [`docs/archive/V5/change_manifest.json`](/D:/构想/stock-assistant/docs/archive/V5/change_manifest.json)
  - 基线标签、提交列表、变更文件清单、文件归类、修改原因
- [`docs/archive/V5/verification.md`](/D:/构想/stock-assistant/docs/archive/V5/verification.md)
  - 后端测试、前端构建、交互式 smoke 的命令与结果

## Git 查询建议

- 文件范围：`git diff --name-only v5.0-draft..HEAD`
- 提交范围：`git log --oneline v5.0-draft..HEAD`
- 单文件追踪：`git log --oneline -- <path>`
