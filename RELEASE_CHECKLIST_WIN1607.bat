@echo off
setlocal
cd /d "%~dp0"
if not exist .venv-build\Scripts\python.exe (
  echo Run BUILD_WINDOWS_EXE.bat first.
  exit /b 1
)
.venv-build\Scripts\python.exe -m scripts.release_check %*
exit /b %ERRORLEVEL%
