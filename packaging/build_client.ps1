# 构建 WPF 桌面客户端（需要 .NET 8 SDK；产物为单文件 DocTools.exe）
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

& dotnet publish desktop\DocTools\DocTools.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -o dist\DocTools-client
if ($LASTEXITCODE -ne 0) { throw "dotnet publish 失败" }

Write-Host "输出目录: dist\DocTools-client\DocTools.exe"