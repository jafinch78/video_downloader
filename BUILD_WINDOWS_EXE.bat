@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
if /i "%~1"=="--internal-run" goto :run
set "VD_PAUSE=1"
set "VD_MANUAL="
:parse
if "%~1"=="" goto :launch
if /i "%~1"=="--no-pause" (
  set "VD_PAUSE=0"
  shift
  goto :parse
)
if /i "%~1"=="--manual-confirmed" (
  set "VD_MANUAL=-ManualConfirmed"
  shift
  goto :parse
)
echo ERROR: Unknown option "%~1". Supported: --no-pause and --manual-confirmed for validation.
if "%VD_PAUSE%"=="1" pause
exit /b 2
:launch
if not exist "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" goto :bootstrap_failure
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run_logged.ps1" -Task Build %VD_MANUAL%
set "VD_RESULT=%ERRORLEVEL%"
echo.
echo Logs are saved in "%~dp0logs". Exit code: %VD_RESULT%
if "%VD_PAUSE%"=="1" pause
exit /b %VD_RESULT%
:bootstrap_failure
if not exist logs mkdir logs
>"logs\build-bootstrap-error.log" echo ERROR: Windows PowerShell is missing. Logging helper could not start.
type "logs\build-bootstrap-error.log"
if "%VD_PAUSE%"=="1" pause
exit /b 1
:run
shift
echo [1/9] Checking required Python 3.12.7 x64...
py -3.12 -c "from scripts.build_support import require_release_runtime; require_release_runtime()"
if errorlevel 1 exit /b %ERRORLEVEL%
echo [2/9] Preparing isolated build environment...
if exist .venv-build\Scripts\python.exe goto :environment_ready
py -3.12 -m venv .venv-build
if errorlevel 1 exit /b %ERRORLEVEL%
:environment_ready
.venv-build\Scripts\python.exe -c "from scripts.build_support import require_release_runtime; require_release_runtime()"
if errorlevel 1 exit /b %ERRORLEVEL%
echo [3/9] Installing pinned build and runtime dependencies...
.venv-build\Scripts\python.exe -m pip install -r requirements-build.txt
if errorlevel 1 exit /b %ERRORLEVEL%
echo [4/9] Checking media-tool provenance, hashes, licenses and source...
.venv-build\Scripts\python.exe -m scripts.build_support
if errorlevel 1 exit /b %ERRORLEVEL%
set "PATH=%CD%\assets;%PATH%"
echo [5/9] Testing local dependencies, native libraries, certificates and Tcl/Tk...
.venv-build\Scripts\python.exe -m pip check
if errorlevel 1 exit /b %ERRORLEVEL%
.venv-build\Scripts\python.exe -m scripts.check_dependencies --output logs\local-dependencies.json
if errorlevel 1 exit /b %ERRORLEVEL%
echo [6/9] Running application, GUI, media and packaging tests...
.venv-build\Scripts\python.exe -m unittest discover -v
if errorlevel 1 exit /b %ERRORLEVEL%
echo [7/9] Building the real Windows portable application...
.venv-build\Scripts\python.exe -m PyInstaller --noconfirm --clean packaging\VideoDownloader.spec
if errorlevel 1 exit /b %ERRORLEVEL%
echo [8/9] Copying documentation and third-party licenses...
copy /y README.md dist\VideoDownloader\README.txt >nul
if errorlevel 1 exit /b %ERRORLEVEL%
copy /y THIRD_PARTY_NOTICES.md dist\VideoDownloader\THIRD_PARTY_NOTICES.md >nul
if errorlevel 1 exit /b %ERRORLEVEL%
.venv-build\Scripts\python.exe -m scripts.collect_licenses
if errorlevel 1 exit /b %ERRORLEVEL%
echo [9/9] Checking the actual bundle and executing its dependency/media smoke test...
.venv-build\Scripts\python.exe -m scripts.verify_delivery --folder dist\VideoDownloader
if errorlevel 1 exit /b %ERRORLEVEL%
.venv-build\Scripts\python.exe -m scripts.bundle_check --report logs\bundled-dependencies.json
if errorlevel 1 exit /b %ERRORLEVEL%
echo BUILD SUCCESS: dist\VideoDownloader\VideoDownloader.exe exists and its bundled dependency/media checks passed.
echo Windows 1607 compatibility remains pending until RELEASE_CHECKLIST_WIN1607.bat passes on that OS.
exit /b 0
