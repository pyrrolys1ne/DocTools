# 构建 DocTools 安装器（Inno Setup 6）。依赖 dist\DocTools-win-x64（package.ps1 产物）。
# 用法：.\packaging\build_installer.ps1            # 先 package.ps1 再编译安装器
#       .\packaging\build_installer.ps1 -SkipBuild  # 仅用现有构建产物
# 未安装 Inno Setup 时：winget install JRSoftware.InnoSetup
param(
    [switch]$SkipBuild,
    [string]$Iscc = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not $SkipBuild) {
    & .\packaging\package.ps1
    if ($LASTEXITCODE -ne 0) { throw "package.ps1 失败" }
}

if (-not $Iscc) {
    # choco 安装会创建 PATH shim（C:\ProgramData\chocolatey\bin\ISCC.exe），优先命中
    $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($cmd) { $Iscc = $cmd.Source }
}
if (-not $Iscc) {
    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )
    $Iscc = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $Iscc -or -not (Test-Path $Iscc)) {
    throw "未找到 Inno Setup 6（ISCC.exe）。安装：winget install JRSoftware.InnoSetup"
}

# 版本号与 pyproject.toml 保持单一来源
$match = Select-String -Path pyproject.toml -Pattern '^version = "([^"]+)"'
if (-not $match) { throw "无法从 pyproject.toml 读取版本号" }
$version = $match.Matches[0].Groups[1].Value

& $Iscc "packaging\installer.iss" `
    "/DSourceDir=$Root\dist\DocTools-win-x64" `
    "/DOutputDir=$Root\dist" `
    "/DAppVersion=$version"
if ($LASTEXITCODE -ne 0) { throw "ISCC 编译失败" }

Write-Host "安装器已生成: dist\DocTools-Setup-$version-x64.exe"
