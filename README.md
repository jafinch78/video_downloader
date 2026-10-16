# Video Downloader

A desktop GUI for saving a website video **with audio** to a selected local folder. Paste a URL, choose a folder, and click **Download**. Progress and errors appear in the window; **Cancel** stops the download and media-tool processes.

**Current delivery: tested application source and Windows build tools. No Windows EXE has been built or certified yet.** The development machine is Linux. Windows 10 version 1607 x64 (build 14393) is the release target, not a verified compatibility claim for this application.

## Standalone use

The intended Windows release is a portable ZIP. Extract the **whole** `VideoDownloader` folder, then open `VideoDownloader.exe`. Keep `_internal` and the bundled files beside the EXE. No Python installation or package download is required on the destination computer. Internet access is required to fetch videos, but startup does not require internet.

- One video per action. Playlists, browser logins, DRM, and automatic updates are not included.
- Site support comes from bundled yt-dlp. Websites can change; some require authentication, JavaScript runtimes, or other capabilities outside this bundle. An unsupported site produces an error; there is no promise of universal support.
- Prefer MP4-compatible video/audio. Other streams merge into MKV without quality-losing re-encoding.
- The final file must contain audio and video. A silent source produces an error.
- Completed files are never overwritten; duplicate names receive a numbered suffix.
- Cancelled/failed downloads retain `.video-downloader-partials` in the selected folder for retry. Small ownership-lock files also remain after successful downloads. You can delete this folder when no application instance is downloading there. Concurrent downloads of the same URL to the same folder are rejected safely.
- The application stores no login credentials. URLs with embedded usernames/passwords are rejected; URL details are redacted from diagnostics.

## Develop from source

Use the existing checkout; cloud tasks are already isolated and need no additional worktree.

Linux development requires Python 3.12 with Tkinter and `ffmpeg`/`ffprobe` on PATH. A graphical display is required for the GUI. Python 3.12.14 was used for Linux tests; releases use exactly Python 3.12.7 x64.

```sh
cd /workspace/video_downloader
python -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m video_downloader
```

On Windows, use `py -3.12 -m venv .venv`, then `.venv\Scripts\python.exe -m pip install -r requirements-lock.txt` and `.venv\Scripts\python.exe -m video_downloader`. Install Python with Tcl/Tk. For source mode, put FFmpeg/FFprobe on PATH or prepare the bundled assets below.

Run tests from the repository root:

```sh
.venv/bin/python -m unittest discover -v
```

Tests generate tiny local media and use a loopback HTTP server; they do not depend on a third-party video site. FFmpeg and FFprobe are required. Logging execution tests additionally require Windows PowerShell 5.1 or PowerShell on Linux (the cloud setup retains a verified portable copy). Skipped logging tests do not verify the logger. GUI tests skip without a display: a run with skipped GUI tests does not verify the GUI. With Xvfb running, use `DISPLAY=:97 .venv/bin/python -m unittest discover -v` (substitute its actual display).

## Prepare Windows media tools

The build now prepares missing assets automatically at step 4. `scripts/build_support.py` downloads Gyan's pinned FFmpeg 6.1.1 x64 essentials ZIP and the matching upstream FFmpeg source, verifies the binary SHA-256 against Microsoft's winget manifest and source SHA-512 against Microsoft's vcpkg recipe, and creates the required asset manifest. Downloads are cached in `%TEMP%\VideoDownloader-build-cache`; later builds validate and reuse existing assets. Existing unrecognized files are not overwritten. First setup needs internet access. The target Windows execution checks still determine compatibility; archive verification alone does not certify Windows 1607.

The automatic `ffmpeg-source.zip` contains the verified **upstream FFmpeg source**, not all vendor third-party dependency/build sources. This scope is printed and recorded in the manifest. Asset checks establish identity and runtime packaging, not complete corresponding-source compliance for redistributing the vendor binaries. The manual preparation method below remains available when assembling the full vendor-specific source set.

### Manual/custom asset preparation

Use a trusted **static Windows x64 ZIP build** of FFmpeg/FFprobe. Verify its publisher's SHA-256 before importing it. The ZIP must contain exactly one `ffmpeg.exe`, `ffprobe.exe`, and `LICENSE.txt`. Obtain the corresponding source/build/dependency-source ZIP required by that build's license, and its authoritative checksum. Do not substitute a self-generated hash for a publisher checksum.

The application uses the tools as separate executables. Neither the Python/PyInstaller versions nor a modern Windows FFmpeg build alone establish Windows 1607 support. The current BtbN README guarantees Windows 10 22H2, with no guarantee for older versions. An appropriately compatible media-tool build and the native checks below remain prerequisites. Gyan's distribution host was inaccessible from this cloud instance; verification was not bypassed.

From the repository root, using your actual downloaded paths, authoritative URL, and hashes:

```bat
py -3.12 -m scripts.prepare_ffmpeg --archive C:\downloads\ffmpeg-static.zip --sha256 PUBLISHER_BINARY_SHA256 --source-url https://publisher.example/exact-build.zip --source-archive C:\downloads\ffmpeg-source.zip --source-sha256 PUBLISHER_SOURCE_SHA256
```

The command checks both archive hashes before importing into ignored `assets/`, records provenance, and refuses to overwrite existing assets. Review the exact source contents and license for your selected build. Source provenance and notices travel with the distribution. It does not download or execute unverified binaries.

## Build the portable Windows EXE

On Windows with **Python 3.12.7 x64** and Tcl/Tk:

```bat
BUILD_WINDOWS_EXE.bat
```

This creates `.venv-build`, installs pinned dependencies, checks asset hashes, performs explicit local dependency/Tcl/Tk tests, runs the suite, builds a **windowed one-folder** EXE with **PyInstaller 6.14.1**, collects licenses, checks bundle contents, and executes the actual EXE dependency/media smoke test. The script reports build success only after all those steps pass. Output: `dist\VideoDownloader\VideoDownloader.exe`. A frozen worker uses a private event file, so progress does not depend on a console being present. Heavy extractor imports occur in the download worker, keeping GUI startup lightweight.

The packaging method follows the Toyota CYD35 related application's [documented Windows 1607 validation](https://github.com/jafinch78/Toyota-Hybrid-CYD35-Diagnostic-CAN-Logger/blob/main/docs/releases/video-narration-transcriber-v1.0.5/VALIDATION.md). That record validates that other application, not this downloader's new dependency combination.

## Native Windows 1607 release checks

Run on **native Windows 10 x64 version 1607 build 14393**:

```bat
RELEASE_CHECKLIST_WIN1607.bat
```

The automated check rejects other OS builds, runs the actual frozen EXE's diagnostic mode, generates separate audio/video streams, serves them locally, downloads/merges them through the frozen worker, checks both streams, and records runtime versions and hashes in `logs\validation-win1607.json`. Windows build tooling/Python can be present for this automated harness; that does not establish no-Python startup on the destination machine.

Also perform these manual checks using the exact extracted distribution:

1. With no installed Python and networking disabled, launch the GUI and confirm all controls appear.
2. Re-enable networking and download a known supported video to a path containing spaces and non-ASCII characters. Play the saved file and confirm both picture and sound.
3. Repeat the download and confirm the existing file remains unchanged.
4. Cancel during extraction/download and again during merging. Confirm responsiveness and that neither the worker nor FFmpeg remains running. Confirm a retry works.
5. Test a silent source, an unsupported URL, an unwritable destination, and a failed connection; confirm errors restore the Download button and never show success.
6. Close during a download, decline once and accept once; confirm the prompt and cleanup.

Only after actually completing those checks, record the attestation:

```bat
RELEASE_CHECKLIST_WIN1607.bat --manual-confirmed
.venv-build\Scripts\python.exe -m scripts.package_release
```

The ZIP and SHA-256 are written under `dist\releases`. ZIP creation alone is not certification. Preserve the validation JSON beside the release. Linux tests, dependency-wheel availability, and emulation do not substitute for these native checks.

## Maintainer notes

Refresh dependencies through a reviewed rebuild and repeat the Windows release gates. The app never self-updates or installs missing runtimes. `requirements.txt` identifies the extractor feature set; `requirements-lock.txt` pins its resolved dependencies; `requirements-build.txt` adds Windows build tools. Application worker events are JSON-lines in a private temporary directory, removed after exit. No external service or API key is needed.


## Build logs, pauses, and required dependency checks

Both BAT entry points stream progress, stdout and stderr into timestamped UTF-8 `logs/build-*.log` or `logs/validate-*.log` files. Each has a matching JSON summary with start/end times, duration, success/failure and the real exit code. The console prints the log path and pauses on **both success and failure**. Use `--no-pause` explicitly for automation. Windows PowerShell 5.1 is required by the logger and is included with Windows 10 1607. If PowerShell cannot launch, a bootstrap-error log and the pause remain available.

```bat
BUILD_WINDOWS_EXE.bat --no-pause
RELEASE_CHECKLIST_WIN1607.bat --no-pause
RELEASE_CHECKLIST_WIN1607.bat --manual-confirmed --no-pause
```

Dependency evidence is separated:

- `logs/local-dependencies.json`: all 11 pinned Python runtime packages must import at their exact versions. The check records module paths and exercises native AES, native Brotli, the certificate store, Tcl/Tk initialization, FFmpeg and FFprobe. `pip check` additionally checks installed package requirements.
- `logs/bundled-dependencies.json`: the **actual built EXE** must pass its `--self-test`, including the same dependency checks, while installed-Python paths are removed. Frozen package imports must resolve inside the bundle. The actual bundled media tools must then generate, download, merge, and probe a local audio/video fixture. This is a general Windows bundle smoke test; it does not certify Windows 1607.
- `logs/validation-win1607.json`: the preceding checks are repeated on the explicitly required native OS, with manual GUI/offline/playback/cancellation checks recorded separately.

`python -m scripts.verify_delivery --folder dist/VideoDownloader` checks the EXE, Python DLL, Visual C runtime DLL, Tcl/Tk data, media tools, notices, sources, and asset hashes. `python -m scripts.verify_delivery --zip PATH` inspects the actual application ZIP. A source ZIP is intentionally rejected by these commands.

`python -m scripts.package_release` now refuses missing/incomplete bundles or an absent, failed, stale or wrong-bundle smoke report. The report binds every bundle file to its hash, including Python DLLs and certificate data; changing any file requires re-running the actual EXE checks. It includes the matching report inside the ZIP and re-verifies archive contents. Packaging tests use deliberately non-runnable structural fixtures; they do not count as Windows execution.

Some website extractors require optional JavaScript runtimes, browser authentication, or services outside the declared bundle. Such capabilities remain outside this version. Package-import checks do not establish that every website is supported.
