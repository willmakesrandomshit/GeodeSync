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
    try {
        $signature = Set-AuthenticodeSignature -FilePath $exePath -Certificate $cert -TimestampServer 'http://timestamp.digicert.com' -ErrorAction SilentlyContinue
        if (-not $signature) {
            $signature = Set-AuthenticodeSignature -FilePath $exePath -Certificate $cert -ErrorAction SilentlyContinue
        }
        Write-Output "Signature Status: $($signature.Status)"
    } catch {
        Write-Warning "Code signing skipped: $_"
    }
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
Copy-Item $exePath (Join-Path $repoRoot 'dist\GeodeSync.exe') -Force
if (Test-Path 'C:\Users\Owner\Downloads') {
    Copy-Item $exePath 'C:\Users\Owner\Downloads\GeodeSync.exe' -Force
}
Copy-Item $zipPath (Join-Path $repoRoot 'dist\GeodeSync-Windows.zip') -Force
Write-Output "Built $zipPath"
