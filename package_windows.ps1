$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot
$version = (Get-Content 'version.json' -Raw | ConvertFrom-Json).app_version
if (-not $version) { throw 'version.json does not contain app_version.' }

python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name GeodeSync --icon icon.ico --version-file version_info.txt `
    --manifest app.manifest --add-data 'icon.ico;.' main.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed to build GeodeSync.exe.' }

$cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert -ErrorAction SilentlyContinue | Select-Object -First 1
if ($cert) {
    Set-AuthenticodeSignature -FilePath 'dist\GeodeSync.exe' -Certificate $cert -TimestampServer "http://timestamp.digicert.com" -ErrorAction SilentlyContinue | Out-Null
}

$packageDir = Join-Path $repoRoot "dist\GeodeSync-v$version-Windows"
if (Test-Path $packageDir) { Remove-Item $packageDir -Recurse -Force }
New-Item -ItemType Directory -Path $packageDir | Out-Null
Copy-Item 'dist\GeodeSync.exe' (Join-Path $packageDir 'GeodeSync.exe')
Copy-Item 'README.md' (Join-Path $packageDir 'README.txt')
$batContent = "@echo off`r`npowershell -NoProfile -Command ""Unblock-File -Path '%~dp0GeodeSync.exe' -ErrorAction SilentlyContinue""`r`nstart """" ""%~dp0GeodeSync.exe""`r`n"
Set-Content -Path (Join-Path $packageDir 'Run-GeodeSync.bat') -Value $batContent
$zipPath = Join-Path $repoRoot "dist\GeodeSync-v$version-Windows.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path (Join-Path $packageDir '*') -DestinationPath $zipPath
Write-Output "Built $zipPath"
