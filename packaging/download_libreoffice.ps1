# 下载并解包便携版 LibreOffice 到 bin/libreoffice，作为 word/ppt→pdf 的兜底引擎。
# 用法：
#   .\packaging\download_libreoffice.ps1 -Url <paf.exe 下载直链>
#   .\packaging\download_libreoffice.ps1 -Paf <已下载的 .paf.exe 路径>
# 下载来源（PortableApps 便携版）：https://portableapps.com/apps/office/libreoffice-portable
# 解包后目录结构：bin\libreoffice\program\soffice.exe
# 打包时 docserver.spec 会自动把 bin\libreoffice 打进 docserver（若存在）。
# 说明：仅需执行一次；LibreOffice 为 MPL 2.0，随包分发需保留其 license/CREDITS 文件。
param(
    [string]$Url = "",
    [string]$Paf = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$target = Join-Path $Root "bin\libreoffice"
if (Test-Path $target) {
    Write-Host "bin\libreoffice 已存在，跳过（如需重装请先删除）。"
    exit 0
}

if (-not $Paf) {
    if (-not $Url) { throw "请提供 -Url（paf.exe 下载直链）或 -Paf（已下载的 .paf.exe 路径）" }
    $Paf = Join-Path $env:TEMP "LibreOfficePortable.paf.exe"
    Write-Host "下载便携版 LibreOffice..."
    Invoke-WebRequest -Uri $Url -OutFile $Paf
}
if (-not (Test-Path $Paf)) { throw "找不到 .paf.exe：$Paf" }

$extractRoot = Join-Path $env:TEMP ("lo-portable-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $extractRoot | Out-Null
try {
    # paf.exe 是 NSIS 自解压包，/D 指定解压目录（必须是绝对路径且无引号包裹）
    Write-Host "解包便携版（需 1-2 分钟）..."
    $proc = Start-Process -FilePath (Resolve-Path $Paf) -ArgumentList "/D=$extractRoot" -Wait -PassThru
    if ($proc.ExitCode -ne 0) { throw "paf.exe 解包失败，退出码 $($proc.ExitCode)" }

    # 便携版结构：LibreOfficePortable\App\libreoffice\program\soffice.exe
    $app = Join-Path $extractRoot "LibreOfficePortable\App\libreoffice"
    if (-not (Test-Path (Join-Path $app "program\soffice.exe"))) {
        throw "解包后未找到 soffice.exe，便携版目录结构可能变化，请检查 $extractRoot"
    }
    New-Item -ItemType Directory -Path (Split-Path $target) -Force | Out-Null
    Move-Item -Path $app -Destination $target
    Write-Host "已解包到 $target"
} finally {
    Remove-Item -Recurse -Force $extractRoot -ErrorAction SilentlyContinue
}
Write-Host "完成。打包时 docserver.spec 会自动包含 bin\libreoffice。"
