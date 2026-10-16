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
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run_logged.ps1" -Task Validate %VD_MANUAL%
set "VD_RESULT=%ERRORLEVEL%"
echo.
echo Logs are saved in "%~dp0logs". Exit code: %VD_RESULT%
if "%VD_PAUSE%"=="1" pause
exit /b %VD_RESULT%
:bootstrap_failure
if not exist logs mkdir logs
>"logs\validate-bootstrap-error.log" echo ERROR: Windows PowerShell is missing. Logging helper could not start.
type "logs\validate-bootstrap-error.log"
if "%VD_PAUSE%"=="1" pause
exit /b 1
:run
shift
echo [1/2] Checking the build environment and native Windows 1607 release prerequisites...
if not exist .venv-build\Scripts\python.exe (
  echo ERROR: Build environment is missing. Run BUILD_WINDOWS_EXE.bat first.
  exit /b 1
)
echo [2/2] Running the actual EXE, bundled dependencies and media validation...
if /i "%~1"=="--manual-confirmed" (
  .venv-build\Scripts\python.exe -m scripts.release_check --report logs\validation-win1607.json --manual-confirmed
) else (
  .venv-build\Scripts\python.exe -m scripts.release_check --report logs\validation-win1607.json
)
exit /b %ERRORLEVEL%
