<#
.SYNOPSIS
    一键拉起 TradeLoop 演示：灌合成样例库 → 起后端 → 等就绪 → 起前端 → 开浏览器。

.DESCRIPTION
    比"看截图/GIF"更可验证：任何人在本机一条命令即可复现界面与数据。
    用随仓的合成样例库（不含真实行情），无需 Tushare token。
    后端、前端各自在新窗口运行，关掉窗口即停。

.EXAMPLE
    pwsh scripts/demo_walkthrough.ps1
#>

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $RepoRoot 'backend'
$Frontend = Join-Path $RepoRoot 'frontend'

Write-Host '== TradeLoop 演示一键启动 ==' -ForegroundColor Cyan

# 1) 准备演示数据库（合成样例库 → 工作库）
$sample = Join-Path $RepoRoot 'data/sample.db'
$stock = Join-Path $RepoRoot 'data/stock.db'
if (-not (Test-Path $sample)) {
    throw "缺少合成样例库 $sample（可运行 backend 下的 scripts/generate_sample_db.py 生成）"
}
# 仅当工作库不存在时才用样例库初始化——避免覆盖你已有的数据/凭证（stock.db 可能存了 API key）
if (Test-Path $stock) {
    Write-Host "[1/4] 已存在 data/stock.db，保留不覆盖（如需重置演示数据请手动删除它）" -ForegroundColor Yellow
} else {
    Copy-Item $sample $stock
    Write-Host "[1/4] 演示库就位：$stock" -ForegroundColor Green
}

# 2) 起后端（新窗口）
Start-Process pwsh -ArgumentList @(
    '-NoExit', '-Command',
    "Set-Location '$Backend'; uv run uvicorn app.main:app --host 127.0.0.1 --port 8000"
)
Write-Host '[2/4] 后端启动中（端口 8000）…' -ForegroundColor Green

# 3) 等就绪探针通过（DB 可达且有行情数据）
$ready = $false
foreach ($i in 1..30) {
    Start-Sleep -Seconds 1
    try {
        $resp = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/ready' -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
}
if ($ready) {
    Write-Host '[3/4] 后端已就绪 (/api/ready 200)' -ForegroundColor Green
} else {
    Write-Host '[3/4] 警告：等待就绪超时，仍继续启动前端（可稍后手动刷新）' -ForegroundColor Yellow
}

# 4) 起前端（新窗口）并打开浏览器
Start-Process pwsh -ArgumentList @(
    '-NoExit', '-Command',
    "Set-Location '$Frontend'; pnpm dev"
)
Write-Host '[4/4] 前端启动中（端口 5173）…' -ForegroundColor Green

Start-Sleep -Seconds 4
Start-Process 'http://localhost:5173'

Write-Host ''
Write-Host '演示已拉起：' -ForegroundColor Cyan
Write-Host '  前端   http://localhost:5173'
Write-Host '  API 文档 http://localhost:8000/docs'
Write-Host '关闭对应的两个 pwsh 窗口即可停止后端/前端。' -ForegroundColor DarkGray
