param([switch]$SkipAlloy, [switch]$SkipK6, [switch]$LocalStackOnly)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$toolRoot = Join-Path $repoRoot '.tools/observability'
New-Item -ItemType Directory -Force -Path $toolRoot | Out-Null

function Install-VerifiedArchive($Project, $Version, $Archive, $ChecksumFile, $Owner = 'grafana') {
    $releaseUrl = "https://github.com/$Owner/$Project/releases/download/$Version"
    $archivePath = Join-Path $toolRoot $Archive
    $checksumPath = Join-Path $toolRoot "$Project-checksums.txt"
    if (-not (Test-Path -LiteralPath $archivePath) -or (Get-Item -LiteralPath $archivePath).Length -eq 0) {
        & curl.exe --fail --location --retry 2 --max-time 180 --silent --show-error --output $archivePath "$releaseUrl/$Archive"
        if ($LASTEXITCODE -ne 0) { throw "Download failed: $Archive" }
    }
    Invoke-WebRequest -Uri "$releaseUrl/$ChecksumFile" -OutFile $checksumPath
    $checksumLine = Get-Content -LiteralPath $checksumPath | Where-Object {
        $_ -match ('^[0-9a-fA-F]{64}\s+\*?' + [regex]::Escape($Archive) + '$')
    } | Select-Object -First 1
    if (-not $checksumLine) { throw "Official checksum missing for $Archive" }
    $expectedHash = ($checksumLine -split '\s+')[0]
    $actualHash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash
    if ($actualHash -ne $expectedHash) { throw "SHA256 mismatch for $Archive" }
    Expand-Archive -LiteralPath $archivePath -DestinationPath $toolRoot -Force
    Write-Output "$Project $Version installed; SHA256 verified."
}

if (-not $SkipAlloy -and -not $LocalStackOnly) {
    Install-VerifiedArchive 'alloy' 'v1.20.1' 'alloy-windows-amd64.exe.zip' 'SHA256SUMS'
}
if (-not $SkipK6 -and -not $LocalStackOnly) {
    Install-VerifiedArchive 'k6' 'v2.3.0' 'k6-v2.3.0-windows-amd64.zip' 'k6-v2.3.0-checksums.txt'
}
Install-VerifiedArchive 'prometheus' 'v3.15.0' 'prometheus-3.15.0.windows-amd64.zip' 'sha256sums.txt' 'prometheus'
Install-VerifiedArchive 'loki' 'v3.7.8' 'loki-windows-amd64.exe.zip' 'SHA256SUMS'

# Pinned standalone OSS release and SHA256 from the official download page.
$grafanaArchive = Join-Path $toolRoot 'grafana_13.2.4_38252365904_windows_amd64.tar.gz'
if (-not (Test-Path -LiteralPath $grafanaArchive) -or (Get-Item -LiteralPath $grafanaArchive).Length -eq 0) {
    & curl.exe --fail --location --retry 2 --max-time 180 --silent --show-error --output $grafanaArchive 'https://dl.grafana.com/grafana/release/13.2.4/grafana_13.2.4_38252365904_windows_amd64.tar.gz'
    if ($LASTEXITCODE -ne 0) { throw 'Grafana download failed.' }
}
if ((Get-FileHash -LiteralPath $grafanaArchive -Algorithm SHA256).Hash -ne '3e005ff50fe3bb6b8cb428ef127636fac4ee676bf9b6d819c6a2297d21f4bcbd') {
    throw 'Grafana SHA256 mismatch.'
}
& tar.exe -xzf $grafanaArchive -C $toolRoot
if ($LASTEXITCODE -ne 0) { throw 'Grafana archive extraction failed.' }
Write-Output 'Grafana OSS 13.2.4 installed; SHA256 verified.'
