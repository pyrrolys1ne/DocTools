# 下载并解包便携版 LibreOffice，作为 word/ppt→pdf 的兜底引擎。
# 用法：
#   .\packaging\download_libreoffice.ps1 -Url <下载直链> [-TargetDir <目标目录>]
#   .\packaging\download_libreoffice.ps1 -File <已下载的 .msi 或 .paf.exe> [-TargetDir <目标目录>]
# 支持两种来源：
#   - PortableApps .paf.exe（NSIS 自解压）
#   - TDF 官方 portable .msi（msiexec /a 解包）
# 默认目标目录为 bin\libreoffice（开发/打包用）；安装器调用时用 -TargetDir 指定安装目录。
# 解包后目录结构：<TargetDir>\program\soffice.exe
# 说明：LibreOffice 为 MPL 2.0，随包分发需保留其 license/CREDITS 文件。
param(
    [string]$Url = "",
    [string]$File = "",
    [string]$TargetDir = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not $TargetDir) {
    $TargetDir = Join-Path $Root "bin\libreoffice"
}

if (Test-Path (Join-Path $TargetDir "program\soffice.exe")) {
    Write-Host "$TargetDir 已包含 LibreOffice，跳过（如需重装请先删除）。"
    exit 0
}

if (-not $File) {
    if (-not $Url) { throw "请提供 -Url（下载直链）或 -File（已下载的 .msi/.paf.exe 路径）" }
    $ext = ".paf.exe"
    if ($Url -match "\.msi($|\?)") { $ext = ".msi" }
    $File = Join-Path $env:TEMP ("LibreOfficePortable" + $ext)
    Write-Host "下载便携版 LibreOffice（约 350MB，请耐心等待）..."
    Invoke-WebRequest -Uri $Url -OutFile $File
}
if (-not (Test-Path $File)) { throw "找不到下载文件：$File" }

$extractRoot = Join-Path $env:TEMP ("lo-portable-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $extractRoot | Out-Null
try {
    Write-Host "解包便携版（需 1-2 分钟）..."
    if ($File -match "\.msi$") {
        # TDF 官方 MSI：admin install 解出纯文件布局
        $msiTarget = Join-Path $extractRoot "msi"
        $proc = Start-Process -FilePath "msiexec.exe" `
            -ArgumentList "/a", "`"$((Resolve-Path $File).Path)`"", "/qn", "TARGETDIR=`"$msiTarget`"" `
            -Wait -PassThru
        if ($proc.ExitCode -ne 0) { throw "msiexec 解包失败，退出码 $($proc.ExitCode)" }
    }
    else {
        # PortableApps paf.exe：NSIS 自解压，/D 指定解压目录
        $proc = Start-Process -FilePath (Resolve-Path $File) -ArgumentList "/D=$extractRoot" -Wait -PassThru
        if ($proc.ExitCode -ne 0) { throw "paf.exe 解包失败，退出码 $($proc.ExitCode)" }
    }

    # 递归查找 soffice.exe，定位 libreoffice 根目录（soffice.exe 在 <root>\program\ 下）
    $soffice = Get-ChildItem -Path $extractRoot -Recurse -Filter "soffice.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $soffice) { throw "解包后未找到 soffice.exe，目录结构可能变化，请检查 $extractRoot" }
    $libreRoot = Split-Path -Parent (Split-Path -Parent $soffice.FullName)

    New-Item -ItemType Directory -Path (Split-Path $TargetDir) -Force | Out-Null
    if (Test-Path $TargetDir) { Remove-Item -Recurse -Force $TargetDir }
    Move-Item -Path $libreRoot -Destination $TargetDir
    Write-Host "已解包到 $TargetDir"
} finally {
    Remove-Item -Recurse -Force $extractRoot -ErrorAction SilentlyContinue
}
Write-Host "完成。打包时 docserver.spec 会自动包含 bin\libreoffice。"
