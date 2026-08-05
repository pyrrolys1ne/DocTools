# 构建 docserver（PyInstaller onedir 控制台程序）
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

# 本地开发用 .venv，CI 环境回退到系统 python
$Py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { $Py = "python" }

& $Py -m pip install -q pyinstaller
if ($LASTEXITCODE -ne 0) { throw "pip install pyinstaller 失败" }

& $Py -m PyInstaller packaging\docserver.spec --noconfirm --clean --distpath dist --workpath build\pyinstaller
if ($LASTEXITCODE -ne 0) { throw "PyInstaller 构建失败" }

Write-Host "输出目录: dist\docserver\ (docserver.exe 为入口)"