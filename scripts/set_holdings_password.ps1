# 보유 종목(수량·평단가)과 '내 보유 수익'을 여는 비밀번호를 GitHub Secret으로 저장한다.
#   - scripts\holdings.local.json  →  HOLDINGS_JSON   (이 파일은 .gitignore로 저장소에 올라가지 않음)
#   - 입력한 비밀번호               →  HOLDINGS_PASSWORD
# 사용: powershell -ExecutionPolicy Bypass -File scripts\set_holdings_password.ps1
# 수량·평단가가 바뀌면 holdings.local.json을 고치고 다시 실행 (비밀번호는 Enter로 건너뛰면 그대로 유지).
$ErrorActionPreference = "Stop"
$repo = "choisynkyu-ctrl/korea-news"
$gh = (Get-Command gh -ErrorAction SilentlyContinue).Source
if (-not $gh) { $gh = "C:\Program Files\GitHub CLI\gh.exe" }

$file = Join-Path $PSScriptRoot "holdings.local.json"
if (Test-Path $file) {
    $json = Get-Content $file -Raw -Encoding UTF8
    try { $n = @($json | ConvertFrom-Json).Count } catch { Write-Host "[실패] holdings.local.json 형식이 잘못됐습니다." -ForegroundColor Red; exit 1 }
    $json | & $gh secret set HOLDINGS_JSON --repo $repo
    if ($LASTEXITCODE -ne 0) { Write-Host "[실패] HOLDINGS_JSON 저장 실패. gh auth status 를 확인하세요." -ForegroundColor Red; exit 1 }
    Write-Host "[OK] HOLDINGS_JSON 저장 ($n 종목)" -ForegroundColor Green
} else {
    Write-Host "holdings.local.json이 없어 보유 종목은 건너뜁니다." -ForegroundColor Yellow
}

function Read-Plain([string]$prompt) {
    $s = Read-Host $prompt -AsSecureString
    $b = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)
    try { [Runtime.InteropServices.Marshal]::PtrToStringBSTR($b) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($b) }
}

while ($true) {
    $p1 = Read-Plain "대시보드 '내 보유 수익' 비밀번호 (Enter = 바꾸지 않음)"
    if ($p1.Length -eq 0) { Write-Host "비밀번호는 그대로 둡니다."; exit 0 }
    if ($p1.Length -lt 4) { Write-Host "너무 짧습니다. 다시 입력하세요." -ForegroundColor Yellow; continue }
    $p2 = Read-Plain "한 번 더 입력"
    if ($p1 -ne $p2) { Write-Host "두 번 입력한 값이 다릅니다. 다시 입력하세요." -ForegroundColor Yellow; continue }
    break
}
$p1 | & $gh secret set HOLDINGS_PASSWORD --repo $repo
if ($LASTEXITCODE -ne 0) { Write-Host "[실패] HOLDINGS_PASSWORD 저장 실패. gh auth status 를 확인하세요." -ForegroundColor Red; exit 1 }
Write-Host "[OK] HOLDINGS_PASSWORD 저장. 다음 실행(매일 06:20)부터 대시보드 '내 보유' 탭에서 이 비밀번호로 열립니다." -ForegroundColor Green
