# Qiita API v2 — blog-draft.md を公開（要 QIITA_ACCESS_TOKEN）
# 取得: https://qiita.com/settings/applications → Personal access tokens

param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$draft = Join-Path $root "docs\demo\blog-draft.md"

if (-not $env:QIITA_ACCESS_TOKEN) {
    Write-Error "QIITA_ACCESS_TOKEN が未設定です。Qiita Settings → Applications でトークンを発行してください。"
}

$bodyText = Get-Content $draft -Raw -Encoding UTF8
# 先頭 H1 は Qiita タイトル欄用のため本文から除去
$bodyText = $bodyText -replace '(?m)^#\s+.+?\r?\n', '', 1

$payload = @{
    title = "Conjunction Alert Simulator を作った — 軌道力学と衝突回避の縮小版"
    body  = $bodyText.Trim()
    tags  = @(
        @{ name = "Python" }
        @{ name = "FastAPI" }
        @{ name = "宇宙" }
        @{ name = "OSS" }
        @{ name = "Docker" }
        @{ name = "SGP4" }
    )
    private = $false
}

if ($DryRun) {
    Write-Output "DryRun: title=$($payload.title), body length=$($payload.body.Length)"
    exit 0
}

$json = $payload | ConvertTo-Json -Depth 4 -Compress
$response = Invoke-RestMethod `
    -Method Post `
    -Uri "https://qiita.com/api/v2/items" `
    -Headers @{ Authorization = "Bearer $env:QIITA_ACCESS_TOKEN" } `
    -ContentType "application/json; charset=utf-8" `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($json))

Write-Output "Published: $($response.url)"
$response.url | Set-Content (Join-Path $root "docs\QIITA_PUBLISHED_URL.txt") -Encoding UTF8
