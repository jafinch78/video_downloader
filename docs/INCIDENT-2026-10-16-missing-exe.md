# Missing EXE, build diagnostics, and dependency verification

## Confirmed failure

The user requested a standalone Windows GUI executable. The delivered `VideoDownloader-0.1.0-source.zip` contains no EXE. The advertised `dist\VideoDownloader\VideoDownloader.exe` path describes a future build output; it was never created here. The archive audit is retained in [missing-exe-audit.json](validation/missing-exe-audit.json). The initial delivery status explicitly documents the missing build in [README.md:5](../README.md#video-downloader) and [the initial validation record](VALIDATION.md).

## Root cause

The release handoff failed at the build/artifact boundary. The implementation and tests ran on Linux, while the selected PyInstaller toolchain requires a Windows build and verified Windows media-tool assets. Neither prerequisite was supplied. I then used `git archive` to package tracked source and uploaded that archive. This bypassed the application-release packager and never generated its expected EXE. Although later messages identified the artifact as source-only, the original executable delivery requirement remained unsatisfied.

The acceptance mistake was treating source implementation and Linux test success as sufficient to end the task without the requested runnable artifact. A source archive is useful developer material, but it cannot serve as the standalone application requested here. The output path should have been presented strictly as pending until a real file and an inspected application archive existed.

Two additional gaps made troubleshooting harder:

1. The BAT entry points consisted of commands and early exits without a default pause or persistent logging. A double-clicked window could close before errors could be read. Errors were collapsed to exit code 1, losing the failing tool's actual code.
2. Source tests exercised parts of the dependency stack, but there was no explicit all-pinned-package runtime inventory and no completed frozen-bundle test. A package declaration, installed wheel, or MZ header is insufficient evidence that the distributed program can load and use its dependencies.

The missing Windows build is still an external prerequisite. Correcting checks and documentation does not generate an EXE.

## Corrections

- Both BAT entry points now display phases, retain live stdout/stderr in timestamped UTF-8 logs, write JSON start/end/duration/result summaries, preserve the tool's exit code, and pause by default on success and failure. `--no-pause` is explicit automation behavior. Windows PowerShell bootstrap failure gets a persistent error log.
- `scripts.check_dependencies` loads all 11 exact pinned runtime packages, records module paths, exercises native AES/Brotli and TLS certificates, initializes Tcl/Tk, and runs FFmpeg/FFprobe. Failure details are retained in JSON.
- The EXE's `--self-test` runs those checks inside the frozen process. Imported packages must come from the portable bundle. The bundle smoke removes installed-Python paths, executes bundled tools, downloads and merges a controlled fixture, and verifies audio/video streams. Worker errors are retained in the report even if the worker fails.
- `scripts.verify_delivery` rejects missing EXEs, Python DLLs, certificates, Tcl/Tk data, media tools, source/notices and incomplete archives. It deliberately rejects source-only ZIPs.
- A passing bundle report hashes every bundled file. `scripts.package_release` requires a passing report for that exact EXE, dependency versions and whole-file inventory, includes the report in the archive, and inspects the final ZIP. Replacing a DLL or certificate after testing invalidates packaging.
- `AGENTS.md` records the user's requirements so future work retains logs, pauses and local/bundled dependency checks. Source and application ZIPs must remain clearly labeled. Source archives exclude previous release archives to avoid recursive packaging.

## Evidence and limits

The local dependency report and full source test output are retained under `docs/validation/`: **45 tests passed with zero failures or skips** in the corrected Linux run. `missing-bundle-linux.log` and its JSON files retain the actual failed application-bundle check, including its timestamp and exit code 1; it correctly reports missing VideoDownloader.exe. Logger success and deliberate failure tests execute the real PowerShell helper, including legacy argument-passing mode. The argument-handling regression was reproduced first, then fixed by using an actual temporary Python script rather than embedded `-c` code.

The review also reproduced packaging acceptance after modifying a DLL or certificate following a successful smoke; whole-bundle hashing now rejects this. Regression tests use explicitly non-runnable structural fixtures to exercise packaging rules, not to claim Windows runtime success.

The Linux sandbox initially blocked loopback sockets and display access. The same required checks were rerun with the necessary sandbox permission against a private virtual display; restricted runs were not counted as passing validation.

**Not executed:** Windows BAT interaction/default pauses under CMD, native Windows PowerShell 5.1 execution, actual PyInstaller Windows build, actual Windows bundle dependency/media smoke, and native Windows 10 1607 compatibility checks. PowerShell 7.4.13 on Linux, including legacy argument mode, does not substitute for these checks. The GitHub API build-access check returned Forbidden; Git repository pushes work. No Windows artifact is being represented as built or certified.

## Prevention and next acceptance gate

Do not mark the standalone app delivered until an actual Windows build creates `dist\VideoDownloader\VideoDownloader.exe`, the all-dependency/local and frozen checks pass, the complete installation ZIP is inspected, and an accessible download is verified. Windows 1607 compatibility requires additional native target-OS tests and a compatible media-tool build. Missing prerequisites must remain named blockers; additional source ZIP uploads must not be offered as completion of the EXE requirement.
