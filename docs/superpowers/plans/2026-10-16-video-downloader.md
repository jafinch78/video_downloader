# Portable Video Downloader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Deliver a desktop URL-to-video downloader and a reproducible portable Windows EXE build.

**Architecture:** Tkinter owns the UI and polls structured events from a supervised worker process. The worker embeds yt-dlp, uses bundled FFmpeg/FFprobe, and verifies completed media before reporting success. Windows builds bundle the runtime into a portable folder.

**Tech Stack:** Python 3.12.7 x64 release runtime, Tkinter, yt-dlp, FFmpeg/FFprobe, PyInstaller 6.14.1, unittest.

**Spec:** `docs/superpowers/specs/2026-10-16-video-downloader-design.md`

## Global Constraints

- Target Windows 10 version 1607 x64 (build 14393).
- Use Python 3.12.7 x64 and PyInstaller 6.14.1 for the Windows release.
- Distribute a portable folder as a ZIP; no installed Python is required.
- Internet is required to download media; application startup requires no network.
- One video per action; no playlists, DRM decryption, login management, or automatic updates.
- Preserve TLS verification, completed files, and resumable partial downloads.
- Prefer MP4-compatible streams; use MKV when necessary without re-encoding.
- Success requires a final file containing both video and audio.
- Use the existing isolated checkout; do not create another worktree.
- Linux tests do not establish Windows EXE or Windows 1607 compatibility.

## Review Focus

- URLs with credentials or signed query strings must not leak those values into status diagnostics (Task 1).
- Existing output files and repeated downloads must not silently overwrite completed media (Task 2).
- Cancellation during extraction or FFmpeg merging must terminate descendants and restore idle state (Task 3).
- Paths containing spaces and non-ASCII characters must survive worker launch and media handling (Tasks 2–4).
- A downloaded silent video or failed merge must never produce a success event (Task 2).

## File Structure

- `video_downloader/validation.py`: input validation and diagnostic redaction.
- `video_downloader/runtime.py`: frozen/source asset paths and subprocess commands.
- `video_downloader/worker.py`: yt-dlp integration, JSON events, media verification.
- `video_downloader/controller.py`: subprocess supervision, queue, cancellation.
- `video_downloader/gui.py`, `video_downloader/__main__.py`, `run_gui.py`: GUI and frozen/source dispatch.
- `tests/test_validation.py`, `tests/test_worker.py`, `tests/test_controller.py`, `tests/test_gui.py`, `tests/test_integration.py`: corresponding behavior tests.
- `requirements.txt`, `requirements-build.txt`, `.gitignore`: pinned dependencies and generated-file exclusions.
- `packaging/VideoDownloader.spec`, `BUILD_WINDOWS_EXE.bat`, `RELEASE_CHECKLIST_WIN1607.bat`: build and native verification entry points.
- `scripts/release_check.py`, `scripts/package_release.py`: artifact checks and release ZIP/checksums.
- `README.md`, `THIRD_PARTY_NOTICES.md`: usage, build prerequisites, limitations, and licenses.

### Task 1: Validated inputs and runtime paths

**Interfaces:** Produce `validate_url(value: str) -> str`, `validate_destination(value: str) -> pathlib.Path`, `redact_diagnostic(text: str) -> str` in validation.py; `asset_path(name: str) -> pathlib.Path` and `worker_command(url: str, destination: pathlib.Path) -> list[str]` in runtime.py. Invalid inputs raise `ValueError` with a user-facing explanation. Frozen commands relaunch the executable with a private worker flag; source commands use `sys.executable -m video_downloader.worker`.

- [ ] Write failing tests for HTTP/HTTPS acceptance, malformed URLs, non-HTTP schemes, credential rejection, writable directories, missing paths, query/credential redaction, and source/frozen asset resolution. Assert a URL containing `?token=secret` never leaves `secret` in diagnostics.
- [ ] Run `python -m unittest tests.test_validation -v`; confirm failures reflect missing implementation.
- [ ] Implement validation and runtime interfaces, package initializers, and generated-file exclusions. Probe destination writability with a temporary file that is removed.
- [ ] Run the tests; require all to pass, including Unicode destination paths and invocation argument preservation.
- [ ] Commit this independently testable foundation.

### Task 2: Download worker and real media verification

**Interfaces:** Consume Task 1. Produce `run_download(url: str, destination: pathlib.Path, emit: Callable[[dict], None]) -> pathlib.Path`, `verify_media(path: pathlib.Path) -> None`, and CLI `python -m video_downloader.worker --url URL --destination PATH`. Events have `type` equal to `status`, `progress`, `complete`, or `error`; completion includes `path`, progress includes `percent` or null. Worker stdout is JSON-lines only; process exits nonzero on failure. FFprobe must establish audio and video streams before completion.

- [ ] Write failing worker tests asserting `noplaylist`, TLS verification, no overwrite, audio-required selection, MP4 preference/MKV fallback, progress normalization, redacted errors, and no completion on merge/probe failure. Use dependency fakes for extractor outcomes.
- [ ] Run `python -m unittest tests.test_worker -v`; confirm relevant failures.
- [ ] Select a published yt-dlp version supporting Python 3.12, record its exact pin in requirements.txt, install in an isolated `.venv`, and implement the worker. Use absolute FFmpeg paths, yt-dlp output sanitization and title/ID templates, progress/postprocessor hooks, and final output detection after postprocessing.
- [ ] Add integration tests that generate tiny audio/video media with FFmpeg and serve it over local HTTP. Exercise real yt-dlp and FFprobe, assert final audio/video streams, Unicode paths, preserved existing output, silent-media rejection, and meaningful error events.
- [ ] Run `.venv/bin/python -m unittest tests.test_worker tests.test_integration -v`; require the actual media cases to execute and pass. Document required media tools rather than treating skipped integration as validation.
- [ ] Commit the worker, dependency pin, and tests.

### Task 3: Process controller and responsive GUI

**Interfaces:** Consume Tasks 1–2. Produce `DownloadController.start(url: str, destination: pathlib.Path) -> None`, `cancel() -> None`, `poll() -> list[dict]`, and `active: bool`. GUI `main() -> None` polls events on Tk's main thread; worker monitoring runs off that thread. Completion is accepted only with a zero exit and valid completion event. Cancellation produces a terminal status and preserves partial files.

- [ ] Write failing controller tests using real short-lived helper processes: malformed event lines, exit without completion, repeated start prevention, failure, completion, and cancellation of a worker plus descendant during a blocked operation.
- [ ] Run `python -m unittest tests.test_controller -v`; confirm failures.
- [ ] Implement subprocess supervision with argument arrays and no shell. Use process sessions/groups on POSIX and a Windows process-tree termination mechanism; hide console windows. Keep start/cancel/poll nonblocking to Tk.
- [ ] Write GUI tests for field validation, button states, progress/status rendering, default Downloads/home choice, worker failure recovery, and close-confirmation cancellation. Run with a virtual display when available.
- [ ] Implement the URL/folder entries, Browse, Download, Cancel, progress bar, status area, and entry-point worker dispatch. Avoid credentials in output; display the verified final path and preserved-partial notice.
- [ ] Run controller and GUI tests plus the prior suite; perform a GUI launch smoke with a display and test real worker cancellation. Record unavailable display or Windows-specific checks explicitly.
- [ ] Commit the GUI and process lifecycle implementation.

### Task 4: Portable Windows build and release verification

**Interfaces:** Consume all application modules. Build entry point `BUILD_WINDOWS_EXE.bat` produces `dist/VideoDownloader/VideoDownloader.exe`; media tools reside in the bundled asset directory resolved by Task 1. `RELEASE_CHECKLIST_WIN1607.bat` invokes `scripts/release_check.py` against the built EXE and preserves its exit status. `scripts/package_release.py` produces a ZIP and SHA-256 manifest only from an existing build.

- [ ] Write failing tests for build asset validation, missing media-tool/license rejection, ZIP layout, hash correctness, and paths with spaces. Native checklist must reject the wrong OS/build and a nonexistent artifact.
- [ ] Run those tests and confirm failures.
- [ ] Pin PyInstaller 6.14.1 and its resolved build dependencies for Python 3.12.7. Identify a trusted FFmpeg/FFprobe x64 build, verify its published checksum and license, and assess Windows 1607 support. Do not claim compatibility from architecture alone. If no verified redistributable is obtainable, expose an explicit build prerequisite and report the blocker rather than ship uncertain binaries.
- [ ] Implement the PyInstaller one-folder spec and Windows build script with exact Python version/architecture checks, dependency installation, required asset/license checks, and failure propagation. Build-time FFmpeg inputs use an explicitly documented local directory; no unchecked downloads.
- [ ] Implement a frozen diagnostic mode and native checklist that checks Windows build 14393, launches the real EXE, downloads a controlled fixture through the worker path, probes audio/video, and records versions and hashes. Require manual GUI startup without networking, playback, merge cancellation, and Unicode destination checks in the release record.
- [ ] Implement release ZIP/hash packaging and notices. Document launch, refresh/rebuild procedure, partial files, unsupported-site behavior, and developer tests in README.md.
- [ ] Run the complete Linux test suite and display smoke where possible. Build on Windows only if a runner is available; run native Windows 1607 gates only on that OS. Preserve unrun status for unavailable gates and do not label an unbuilt EXE as delivered.
- [ ] Commit build scripts, documentation, notices, and verification results.

### Task 5: Final review and development environment persistence

**Interfaces:** Consume the completed source tree and test commands. Deliver a reproducible development setup and an evidence-based completion report.

- [ ] Review the full diff against the spec, especially overwrite handling, credential redaction, process trees, frozen asset paths, and false completion. Fix confirmed defects with regression tests.
- [ ] Run the complete meaningful suite once after final fixes, inspect counts and results, and check `git status --short` for unintended files.
- [ ] Execute reproducible dependency-install and source-startup instructions in the checkout. Save necessary onboarding `install_script` and `start_skill` fields, preserving unrelated configuration. Include existing-checkout guidance and distinguish Linux development from native Windows release gates.
- [ ] Record passed, failed, skipped, and unrun checks separately. Report source/build deliverables, any actual Windows artifact, saved configuration, and outstanding native release requirements accurately.
