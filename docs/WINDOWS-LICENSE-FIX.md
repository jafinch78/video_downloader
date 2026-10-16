# Windows runtime license collection repair

The uploaded 15:12 build log records 45 source tests passing (one POSIX-only
skip), successful local dependencies, and successful PyInstaller EXE/COLLECT.
Step 8 then fails because the collector assumes Tcl's standalone license exists
in the Python installation. The same assumption also affects Tk. This was a
packaging-script error, not a missing Tcl runtime. Existing tests excluded all
runtime licenses and therefore failed to cover the Windows installer layout.

The repair retains installed notices when available, otherwise copies exact
Tcl/Tk 8.6.13 notices from the official CPython dependency source tags, verifying
SHA256 before copying. Python and package licenses remain mandatory. Tests
reproduce a Python installation without standalone Tcl/Tk notices and reject
an altered fallback notice. This does not bypass the frozen dependency/media
checks, which did not execute in the uploaded attempt.

Extract VideoDownloader-runtime-license-fix.zip into the existing source root,
overwriting scripts/collect_licenses.py and adding the two files under
packaging/licenses. Keep prior fixes, assets and .venv-build. Rerun
BUILD_WINDOWS_EXE.bat. Inspect its final log/result; EXE creation alone does not
prove the complete portable folder passes its runtime checks.
