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

$installBat = "@echo off`r`ntitle Installing GeodeSync...`r`necho Installing GeodeSync to Local AppData...`r`nset ""TARGET_DIR=%LOCALAPPDATA%\GeodeSync""`r`nif not exist ""%TARGET_DIR%"" mkdir ""%TARGET_DIR%""`r`ncopy /y ""%~dp0GeodeSync.exe"" ""%TARGET_DIR%\GeodeSync.exe"" >nul`r`npowershell -NoProfile -Command ""Unblock-File -Path '%TARGET_DIR%\GeodeSync.exe' -ErrorAction SilentlyContinue""`r`npowershell -NoProfile -Command ""$ws = New-Object -ComObject WScript.Shell; $d = [Environment]::GetFolderPath('Desktop'); $s = $ws.CreateShortcut((Join-Path $d 'GeodeSync.lnk')); $s.TargetPath = '%TARGET_DIR%\GeodeSync.exe'; $s.WorkingDirectory = '%TARGET_DIR%'; $s.Save(); $sm = [Environment]::GetFolderPath('Programs'); $s2 = $ws.CreateShortcut((Join-Path $sm 'GeodeSync.lnk')); $s2.TargetPath = '%TARGET_DIR%\GeodeSync.exe'; $s2.WorkingDirectory = '%TARGET_DIR%'; $s2.Save()""`r`nstart """" ""%TARGET_DIR%\GeodeSync.exe""`r`n"
Set-Content -Path (Join-Path $packageDir 'Install-GeodeSync.bat') -Value $installBat
$zipPath = Join-Path $repoRoot "dist\GeodeSync-v$version-Windows.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path (Join-Path $packageDir '*') -DestinationPath $zipPath
Write-Output "Built $zipPath"
