# Qiita API v2 — blog-draft.md を公開 / 更新（要 QIITA_ACCESS_TOKEN）
# 取得: https://qiita.com/settings/applications → Personal access tokens

param(
    [switch]$DryRun,
    [switch]$Update
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$draft = Join-Path $root "docs\demo\blog-draft.md"
$urlFile = Join-Path $root "docs\QIITA_PUBLISHED_URL.txt"

if (-not $env:QIITA_ACCESS_TOKEN) {
    Write-Error "QIITA_ACCESS_TOKEN が未設定です。Qiita Settings → Applications でトークンを発行してください。"
}

$bodyText = Get-Content $draft -Raw -Encoding UTF8
# 先頭 H1 は Qiita タイトル欄用のため本文から除去
$bodyText = [regex]::Replace($bodyText, '(?m)^#\s+.+?\r?\n', '', 1)

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

function Get-QiitaItemId {
    param([string]$UrlOrId)
    if ($UrlOrId -match '/items/([0-9a-f]+)$') {
        return $Matches[1]
    }
    if ($UrlOrId -match '^[0-9a-f]+$') {
        return $UrlOrId
    }
    throw "Qiita item ID を URL から抽出できません: $UrlOrId"
}

if ($DryRun) {
    $mode = if ($Update) { "Update" } else { "Create" }
    Write-Output "DryRun ($mode): title=$($payload.title), body length=$($payload.body.Length)"
    if ($Update -and (Test-Path $urlFile)) {
        Write-Output "Item ID: $(Get-QiitaItemId (Get-Content $urlFile -Raw).Trim())"
    }
    exit 0
}

$json = $payload | ConvertTo-Json -Depth 4 -Compress
$headers = @{ Authorization = "Bearer $env:QIITA_ACCESS_TOKEN" }

if ($Update) {
    if (-not (Test-Path $urlFile)) {
        Write-Error "Update には docs/QIITA_PUBLISHED_URL.txt が必要です。"
    }
    $itemId = Get-QiitaItemId (Get-Content $urlFile -Raw).Trim()
    $response = Invoke-RestMethod `
        -Method Patch `
        -Uri "https://qiita.com/api/v2/items/$itemId" `
        -Headers $headers `
        -ContentType "application/json; charset=utf-8" `
        -Body ([System.Text.Encoding]::UTF8.GetBytes($json))
    Write-Output "Updated: $($response.url)"
} else {
    $response = Invoke-RestMethod `
        -Method Post `
        -Uri "https://qiita.com/api/v2/items" `
        -Headers $headers `
        -ContentType "application/json; charset=utf-8" `
        -Body ([System.Text.Encoding]::UTF8.GetBytes($json))
    Write-Output "Published: $($response.url)"
    $response.url | Set-Content $urlFile -Encoding UTF8
}
