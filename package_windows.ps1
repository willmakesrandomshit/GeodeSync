$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot
$version = (Get-Content 'version.json' -Raw | ConvertFrom-Json).app_version
if (-not $version) { throw 'version.json does not contain app_version.' }

$buildDir = Join-Path $repoRoot 'dist\GeodeSync'
$packageDir = Join-Path $repoRoot "dist\GeodeSync-v$version-Windows"
if (Test-Path $buildDir) { Remove-Item $buildDir -Recurse -Force }
if (Test-Path $packageDir) { Remove-Item $packageDir -Recurse -Force }

python -m PyInstaller --noconfirm --clean --onedir --windowed `
    --name GeodeSync --icon icon.ico --version-file version_info.txt `
    --manifest app.manifest --add-data 'icon.ico;.' main.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed to build GeodeSync.' }

$exePath = Join-Path $buildDir 'GeodeSync.exe'
if (-not (Test-Path $exePath)) { throw 'PyInstaller did not produce dist\GeodeSync\GeodeSync.exe.' }

$cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert -ErrorAction SilentlyContinue | Select-Object -First 1
if ($cert) {
    $signature = Set-AuthenticodeSignature -FilePath $exePath -Certificate $cert -TimestampServer 'http://timestamp.digicert.com' -ErrorAction Stop
    if ($signature.Status -ne 'Valid') { throw "Authenticode signing failed: $($signature.StatusMessage)" }
}

New-Item -ItemType Directory -Path $packageDir | Out-Null
Get-ChildItem -Force $buildDir | Copy-Item -Destination $packageDir -Recurse -Force
Copy-Item 'README.md' (Join-Path $packageDir 'README.txt')
Copy-Item 'USER_GUIDE.md' (Join-Path $packageDir 'USER_GUIDE.txt')
$runScript = "@echo off`r`nstart `"`" `"%~dp0GeodeSync.exe`"`r`n"
Set-Content -Path (Join-Path $packageDir 'Run-GeodeSync.bat') -Value $runScript -NoNewline

$zipPath = Join-Path $repoRoot "dist\GeodeSync-v$version-Windows.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path (Join-Path $packageDir '*') -DestinationPath $zipPath
Get-FileHash -Algorithm SHA256 -Path $zipPath |
    ForEach-Object { "$($_.Hash.ToLower())  $([IO.Path]::GetFileName($_.Path))" } |
    Set-Content -Encoding ascii (Join-Path $repoRoot 'dist\SHA256SUMS.txt')
Write-Output "Built $zipPath"
