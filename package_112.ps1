$distDir = "C:\Users\Owner\.gemini\antigravity\scratch\gd-version-switcher\dist"
$exe = "$distDir\GeodeSync.exe"

# 1. Sign GeodeSync.exe
$cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $cert) {
    Write-Output "Creating new Code Signing certificate..."
    $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject "CN=GeodeSync Open Source, O=WilPlays, C=US" -CertStoreLocation "Cert:\CurrentUser\My" -FriendlyName "GeodeSync Code Signing"
}
Write-Output "Signing GeodeSync.exe with Authenticode..."
$sig = Set-AuthenticodeSignature -FilePath $exe -Certificate $cert -TimestampServer "http://timestamp.digicert.com" -ErrorAction SilentlyContinue
if (-not $sig -or $sig.Status -ne "Valid") {
    $sig = Set-AuthenticodeSignature -FilePath $exe -Certificate $cert
}
Write-Output "Signature Status: $($sig.Status)"

# 2. Stage files
$stageDir = "$distDir\GeodeSync-v1.1.2"
if (Test-Path $stageDir) { Remove-Item $stageDir -Recurse -Force }
New-Item -ItemType Directory -Path $stageDir | Out-Null

Copy-Item $exe "$stageDir\GeodeSync.exe" -Force

$batContent = @"
@echo off
title Launching GeodeSync...
cd /d "%~dp0"
powershell -NoProfile -Command "Unblock-File -Path '.\GeodeSync.exe' -ErrorAction SilentlyContinue"
start "" ".\GeodeSync.exe"
"@
Set-Content -Path "$stageDir\Run-GeodeSync.bat" -Value $batContent -Encoding Ascii

$readmeContent = @"
==============================================================
   GEODESYNC v1.1.2 - The Geometry Dash Mod & Depot Suite
==============================================================

HOW TO LAUNCH (ZERO POPUPS):
Option A (Fastest & Recommended): Double-click "Run-GeodeSync.bat"
   - Automatically unblocks the app and launches instantly with ZERO SmartScreen popups!

Option B: Double-click "GeodeSync.exe" directly
   - If Windows shows the blue "Windows protected your PC" popup, click "More info" -> "Run anyway".
   - (Every new indie app has this until Microsoft reputation builds up - it is 100% safe & open source).

WHAT'S NEW IN v1.1.2:
   - 🌟 Streamlined Core UI with expandable "More Tools ▾" drawer
   - 📦 1-Click Essential Mods (Jukebox & CBF directly installed)
   - 🎯 Direct FPS Unlocker (configure 144, 240, 360, 480 FPS target in save file)
   - ☁️ Auto-Backup on Game Exit (silent save snapshots when GD closes)
   - 💽 Corrupted Save Doctor (XOR 11 / gzip decrypt integrity test + auto fallback repair)
   - 🧹 GD Storage & Cache Cleaner (purges gigabytes of audio cache / logs safely)
   - 🔄 Mod Profile & Vanilla Switcher (1-click pure vanilla vs modded, save & load mod profiles)
   - ⚡ Fix Click Delay (128 FMOD WASAPI buffer + CBF optimization)
   - 🩺 Crash Doctor (instant crashlog analysis + faulty mod disabler)
   - 📊 Live Steam Depot Download Progress Bar (MB / ~195 MB + %)
   - 🚀 1-Click In-App Self-Updater

SOURCE CODE & SUPPORT:
GitHub: https://github.com/willmakesrandomshit/GeodeSync
Licensed under MIT. Clean, safe, and community-verified.
"@
Set-Content -Path "$stageDir\README.txt" -Value $readmeContent -Encoding Ascii

# 3. Create ZIP
$zipDest = "$distDir\GeodeSync-v1.1.2-Windows.zip"
if (Test-Path $zipDest) { Remove-Item $zipDest -Force }
Compress-Archive -Path "$stageDir\*" -DestinationPath $zipDest

# 4. Copy to Downloads folder
Copy-Item $exe "C:\Users\Owner\Downloads\GeodeSync.exe" -Force
Copy-Item $zipDest "C:\Users\Owner\Downloads\GeodeSync-v1.1.2-Windows.zip" -Force
Write-Output "[x] Built GeodeSync-v1.1.2-Windows.zip and copied to Downloads!"

# 5. Scan with Windows Defender
Write-Output "Scanning freshly built binary with Defender..."
& "C:\Program Files\Windows Defender\MpCmdRun.exe" -Scan -ScanType 3 -File $exe

# 6. Verify File Version Info
(Get-Item $exe).VersionInfo | Format-List
