@echo off
setlocal
cd /d "%~dp0"
py -3.12 -c "from scripts.build_support import require_release_runtime; require_release_runtime()"
if errorlevel 1 exit /b 1
if not exist .venv-build\Scripts\python.exe (
  py -3.12 -m venv .venv-build
  if errorlevel 1 exit /b 1
)
.venv-build\Scripts\python.exe -c "from scripts.build_support import require_release_runtime; require_release_runtime()"
if errorlevel 1 exit /b 1
.venv-build\Scripts\python.exe -m pip install -r requirements-build.txt
if errorlevel 1 exit /b 1
.venv-build\Scripts\python.exe -m scripts.build_support
if errorlevel 1 exit /b 1
set "PATH=%CD%\assets;%PATH%"
.venv-build\Scripts\python.exe -m unittest discover -v
if errorlevel 1 exit /b 1
.venv-build\Scripts\python.exe -m PyInstaller --noconfirm --clean packaging\VideoDownloader.spec
if errorlevel 1 exit /b 1
copy /y README.md dist\VideoDownloader\README.txt >nul
if errorlevel 1 exit /b 1
copy /y THIRD_PARTY_NOTICES.md dist\VideoDownloader\THIRD_PARTY_NOTICES.md >nul
if errorlevel 1 exit /b 1
.venv-build\Scripts\python.exe -m scripts.collect_licenses
if errorlevel 1 exit /b 1
echo Build complete. Run RELEASE_CHECKLIST_WIN1607.bat on Windows 10 build 14393.
exit /b 0
