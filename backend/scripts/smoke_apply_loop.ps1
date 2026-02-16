param(
  [string]$BaseUrl = "http://127.0.0.1:8000",
  [string]$DevUser = "web_smoke_user"
)

Write-Host "Smoke: GET /api/v1/pets?limit=3"

$feedRaw = curl.exe -s -w "`nHTTP_STATUS:%{http_code}`n" `
  -H "X-Woofer-Dev-User: $DevUser" `
  -H "Accept: application/json" `
  "$BaseUrl/api/v1/pets?limit=3"

$feedHttp = (($feedRaw -split "`n") | Where-Object { $_ -like "HTTP_STATUS:*" } | Select-Object -Last 1) -replace "HTTP_STATUS:", ""
$feedBody = (($feedRaw -split "`n") | Where-Object { $_ -notlike "HTTP_STATUS:*" }) -join "`n"

if ($feedHttp.Trim() -ne "200") {
  Write-Host "HTTP/1.1 $($feedHttp.Trim()) (feed)"
  Write-Host $feedBody
  throw "Feed HTTP $feedHttp"
}

$pets = $feedBody | ConvertFrom-Json
if (-not $pets.ok) {
  Write-Host $feedBody
  throw "Feed not ok"
}
if ($pets.data.items.Count -lt 1) { throw "No pets returned" }

$petId = $pets.data.items[0].pet_id
Write-Host "Using pet_id=$petId"
Write-Host ""

Write-Host "Smoke: POST /api/v1/pets/$petId/apply"
$applyUrl = "$BaseUrl/api/v1/pets/$petId/apply"

$tmpJson = Join-Path $env:TEMP "woofer_apply_body.json"

# Write JSON as UTF-8 WITHOUT BOM
[System.IO.File]::WriteAllText($tmpJson, '{"payload":{}}', (New-Object System.Text.UTF8Encoding($false)))

$applyRaw = curl.exe -s -w "`nHTTP_STATUS:%{http_code}`n" `
  -H "X-Woofer-Dev-User: $DevUser" `
  -H "Accept: application/json" `
  -H "Content-Type: application/json" `
  --data-binary "@$tmpJson" `
  "$applyUrl"

Remove-Item $tmpJson -ErrorAction SilentlyContinue



$applyHttp = (($applyRaw -split "`n") | Where-Object { $_ -like "HTTP_STATUS:*" } | Select-Object -Last 1) -replace "HTTP_STATUS:", ""
$applyBody = (($applyRaw -split "`n") | Where-Object { $_ -notlike "HTTP_STATUS:*" }) -join "`n"

if ($applyHttp.Trim() -ne "200") {
  Write-Host "HTTP/1.1 $($applyHttp.Trim()) (apply)"
  Write-Host $applyBody
  throw "Apply HTTP $applyHttp"
}

Write-Host "HTTP/1.1 200 OK"

$apply = $applyBody | ConvertFrom-Json
if (-not $apply.ok) {
  Write-Host $applyBody
  throw "Apply not ok"
}

if (-not $apply.data.application_id) { throw "Missing data.application_id" }
if ($null -eq $apply.data.apply_url) { throw "Missing data.apply_url" }
if ($null -eq $apply.data.apply_hint) { throw "Missing data.apply_hint" }
if ($null -eq $apply.data.payload) { throw "Missing data.payload" }

Write-Host ""
Write-Host "JSON envelope:"
Write-Host '"ok": true'
Write-Host '"data.application_id" present'
Write-Host '"data.apply_url" present'
Write-Host '"data.apply_hint" present'
Write-Host '"data.payload" present'
Write-Host ""
Write-Host "OK:"
Write-Host " application_id = $($apply.data.application_id)"
Write-Host " email_status   = $($apply.data.email_status)"
Write-Host " apply_url      = $($apply.data.apply_url)"
Write-Host " apply_hint     = $($apply.data.apply_hint)"
