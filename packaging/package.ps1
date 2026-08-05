# 组装 Windows 分发包：DocTools.exe + docserver\ + README.txt -> DocTools-win-x64.zip
# 用法：.\packaging\package.ps1            # 先构建再打包
#       .\packaging\package.ps1 -SkipBuild # 仅用现有构建产物打包
param([switch]$SkipBuild)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not $SkipBuild) {
    & .\packaging\build_server.ps1
    if ($LASTEXITCODE -ne 0) { throw "build_server 失败" }
    & .\packaging\build_client.ps1
    if ($LASTEXITCODE -ne 0) { throw "build_client 失败" }
}

$pkgDir = Join-Path $Root "dist\DocTools-win-x64"
$distDir = Join-Path $Root "dist"
$resolvedPkg = [System.IO.Path]::GetFullPath($pkgDir)
$resolvedDist = [System.IO.Path]::GetFullPath($distDir)
# 安全校验：递归删除前确认目标仍在仓库 dist 目录内
if (-not $resolvedPkg.StartsWith($resolvedDist, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "包目录不在 dist 下，已中止：$resolvedPkg"
}
if (Test-Path $pkgDir) { Remove-Item -Recurse -Force $pkgDir }
New-Item -ItemType Directory -Path $pkgDir | Out-Null

Copy-Item -Path (Join-Path $Root "dist\docserver") -Destination (Join-Path $pkgDir "docserver") -Recurse
Copy-Item -Path (Join-Path $Root "dist\DocTools-client\DocTools.exe") -Destination $pkgDir
Copy-Item -Path (Join-Path $Root "packaging\README.txt") -Destination $pkgDir

$zip = Join-Path $Root "dist\DocTools-win-x64.zip"
if (Test-Path $zip) { Remove-Item -Force $zip }

# Windows Defender 会临时锁住刚复制的大文件，导致 Compress-Archive 偶发失败，重试几次
$maxAttempts = 5
for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
    try {
        Compress-Archive -Path $pkgDir -DestinationPath $zip
        break
    } catch {
        if ($attempt -eq $maxAttempts) { throw }
        Write-Warning "压缩被占用（第 $attempt 次），5 秒后重试：$($_.Exception.Message)"
        Start-Sleep -Seconds 5
    }
}
Write-Host "分发包已生成: $zip"