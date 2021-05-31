# $env:path should contain a path to editbin.exe and signtool.exe

$ErrorActionPreference = "Stop"

mkdir build_scripts\win_build

git status

Write-Output "   ---"
Write-Output "Create venv - python3.7, 3.8 or 3.9 is required in PATH"
Write-Output "   ---"
python -m venv venv
. .\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install wheel pep517
pip install pywin32
pip install pyinstaller==4.2

Write-Output "   ---"
Write-Output "Get PLOTBOSS_INSTALLER_VERSION"
# The environment variable PLOTBOSS_INSTALLER_VERSION needs to be defined
$env:PLOTBOSS_INSTALLER_VERSION = python .\build_scripts\installer-version.py

if (-not (Test-Path env:PLOTBOSS_INSTALLER_VERSION)) {
  $env:PLOTBOSS_INSTALLER_VERSION = '0.0.0'
  Write-Output "WARNING: No environment variable PLOTBOSS_INSTALLER_VERSION set. Using 0.0.0"
  }
Write-Output "Plotboss Version is: $env:PLOTBOSS_INSTALLER_VERSION"
Write-Output "   ---"

Write-Output "   ---"
Write-Output "Build plotboss wheels"
Write-Output "   ---"
pip wheel --use-pep517 -f . --wheel-dir=.\build_scripts\win_build .

Write-Output "   ---"
Write-Output "Install plotboss wheels into venv with pip"
Write-Output "   ---"

Write-Output "pip install plotboss"
pip install --no-index --find-links=.\build_scripts\win_build\ plotboss

Write-Output "   ---"
Write-Output "Use pyinstaller to create plotboss .exe's"
Write-Output "   ---"
pyinstaller --log-level INFO plotboss

Write-Output "   ---"
Write-Output "Windows Installer complete"
Write-Output "   ---"