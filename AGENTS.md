# Project delivery requirements

These requirements capture the user's explicit preferences from the missing-EXE investigation.

- The requested product is a standalone Windows GUI EXE with all required runtime dependencies. A source ZIP or build script does not fulfill an EXE delivery request.
- Before calling an application ZIP deliverable, inspect the actual archive for VideoDownloader/VideoDownloader.exe and the required runtime, Tcl/Tk, media tools, certificate data and notices. Run scripts.verify_delivery and the exact built EXE's dependency/media smoke test. A passing source test suite is not proof of a working frozen application.
- Windows BAT entry points must show progress, retain stdout and stderr in timestamped logs, retain machine-readable success/failure and exit-code results, and pause by default on success and failure. An explicit --no-pause flag supports automation. Do not discard the failing command's exit status.
- Test required dependencies both in the local build environment and inside the extracted bundle. Record versions and load paths; exercise native libraries, TLS certificates, Tcl/Tk, FFmpeg, FFprobe, and actual audio/video downloading/merging. Fail on missing or mismatched dependencies. The frozen check must not fall back to globally installed Python packages or media tools.
- State Windows artifact creation, bundle checks, and native Windows 10 1607 validation separately. Never mark unrun checks passed. No Windows 1607 compatibility claim without native testing on the target OS.
- Work in the existing isolated checkout; no extra worktree is required.
