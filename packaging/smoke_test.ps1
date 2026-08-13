# DocTools 打包产物冒烟测试：启动 docserver，真实跑一次 pdf-to-word 转换。
# 用法：.\packaging\smoke_test.ps1                  # 默认 dist\docserver + .venv
#       .\packaging\smoke_test.ps1 -Python python   # CI 环境（系统 python）
param(
    [string]$DocServer = "dist\docserver\docserver.exe",
    [string]$Python = ".venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path $DocServer)) { throw "找不到 docserver：$DocServer（先运行 packaging\package.ps1）" }

$workDir = Join-Path $env:TEMP ("doctools-smoke-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $workDir | Out-Null
$stdout = Join-Path $workDir "server.log"
$proc = $null

try {
    # 启动 docserver：--port 0 自动选端口，stdout 打印 DOCSERVER_PORT=<port>
    $exeDir = Split-Path (Resolve-Path $DocServer)
    $proc = Start-Process -FilePath (Resolve-Path $DocServer) -ArgumentList "--port", "0" `
        -WorkingDirectory $exeDir -RedirectStandardOutput $stdout -PassThru -WindowStyle Hidden

    # 等待端口行（最多 30 秒）
    $port = $null
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Milliseconds 500
        if (Test-Path $stdout) {
            $line = Get-Content $stdout | Where-Object { $_ -match "^DOCSERVER_PORT=(\d+)$" } | Select-Object -First 1
            if ($line) { $port = $line -replace "^DOCSERVER_PORT=", ""; break }
        }
        if ($proc.HasExited) { throw "docserver 提前退出，日志：$(Get-Content $stdout -Raw -ErrorAction SilentlyContinue)" }
    }
    if (-not $port) { throw "未能从 docserver 输出解析端口（30 秒超时）" }
    $base = "http://127.0.0.1:$port"

    # 1) 健康检查
    $health = Invoke-RestMethod "$base/api/health"
    if ($health.status -ne "ok") { throw "健康检查异常：$($health | ConvertTo-Json -Compress)" }
    Write-Host "SMOKE: 健康检查 OK"

    # 2) 能力清单
    $caps = Invoke-RestMethod "$base/api/v1/capabilities"
    if (-not $caps.engines.pymupdf) { throw "capabilities 缺少 pymupdf 引擎标记" }
    Write-Host "SMOKE: capabilities OK"

    # 3) 用 PyMuPDF 生成测试 PDF，真实跑一次 pdf-to-word
    $pdf = Join-Path $workDir "smoke.pdf"
    $outDocx = Join-Path $workDir "smoke.docx"
    & $Python -c "import fitz; d = fitz.open(); p = d.new_page(); p.insert_text((72, 720), 'DocTools smoke test'); d.save(r'$pdf')"
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $pdf)) { throw "生成测试 PDF 失败" }

    $body = @{ operation = "pdf-to-word"; source_path = $pdf; output_path = $outDocx } | ConvertTo-Json
    $job = Invoke-RestMethod -Method Post -Uri "$base/api/v1/jobs" -ContentType "application/json" -Body $body
    for ($i = 0; $i -lt 120; $i++) {
        Start-Sleep -Milliseconds 500
        $job = Invoke-RestMethod "$base/api/v1/jobs/$($job.id)"
        if ($job.status -in @("done", "failed")) { break }
    }
    if ($job.status -ne "done") { throw "冒烟任务未完成：status=$($job.status) error=$($job.error)" }
    $failed = @($job.results | Where-Object { -not $_.ok })
    if ($failed.Count -gt 0) { throw "存在失败结果：$($failed | ConvertTo-Json -Compress)" }
    if (-not (Test-Path $outDocx)) { throw "未生成输出 docx" }
    $head = [System.IO.File]::ReadAllBytes($outDocx)[0..1]
    if (-not ($head[0] -eq 0x50 -and $head[1] -eq 0x4B)) { throw "输出 docx 不是 zip（PK 魔数不符）" }

    Write-Host "SMOKE OK: pdf-to-word 转换成功（$($job.results.Count) 个结果）"
}
finally {
    if ($proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
    Remove-Item -Recurse -Force $workDir -ErrorAction SilentlyContinue
}
