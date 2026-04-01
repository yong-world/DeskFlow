# ========================================
# 测试：Python ↔ C# 子进程通信
# ========================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  测试：Python ↔ C# 子进程通信" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 获取脚本所在目录的父目录（项目根目录）
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir

# 检查 C# 程序是否已编译
$exePath = Join-Path $projectRoot "csharp\src\DesktopAgent\bin\Debug\net8.0-windows\DesktopAgent.exe"
if (-not (Test-Path $exePath)) {
    Write-Host "[错误] 找不到 DesktopAgent.exe" -ForegroundColor Red
    Write-Host "请先编译 C# 项目：" -ForegroundColor Yellow
    Write-Host "  cd csharp" -ForegroundColor Yellow
    Write-Host "  dotnet build" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "按回车键退出"
    exit 1
}

# 检查记事本是否已打开
$notepadProcess = Get-Process -Name "notepad" -ErrorAction SilentlyContinue

if (-not $notepadProcess) {
    Write-Host "[提示] 记事本未运行，正在启动..." -ForegroundColor Yellow
    Start-Process notepad
    Start-Sleep -Seconds 1
    Write-Host "[成功] 记事本已启动" -ForegroundColor Green
} else {
    Write-Host "[提示] 检测到记事本已运行" -ForegroundColor Green
}

Write-Host ""
Read-Host "按回车键开始测试"

# 切换到 python 目录并运行测试脚本
$pythonDir = Join-Path $projectRoot "python"
Push-Location $pythonDir

Write-Host ""
Write-Host "[运行] uv run python examples/test_inspect.py" -ForegroundColor Green
Write-Host ""

& uv run python examples/test_inspect.py

Pop-Location

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  测试完成" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Read-Host "按回车键退出"
