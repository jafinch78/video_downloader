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

Tests generate tiny local media and use a loopback HTTP server; they do not depend on a third-party video site. FFmpeg and FFprobe are required. GUI tests skip without a display: a run with skipped GUI tests does not verify the GUI. With Xvfb running, use `DISPLAY=:97 .venv/bin/python -m unittest discover -v` (substitute its actual display).

## Prepare Windows media tools

Use a trusted **static Windows x64 ZIP build** of FFmpeg/FFprobe. Verify its publisher's SHA-256 before importing it. The ZIP must contain exactly one `ffmpeg.exe`, `ffprobe.exe`, and `LICENSE.txt`. Obtain the corresponding source/build/dependency-source ZIP required by that build's license, and its authoritative checksum. Do not substitute a self-generated hash for a publisher checksum.

The application uses the tools as separate executables. Neither the Python/PyInstaller versions nor a modern Windows FFmpeg build alone establish Windows 1607 support. The current BtbN README guarantees Windows 10 22H2, with no guarantee for older versions. An appropriately compatible media-tool build and the native checks below remain prerequisites. Gyan's distribution host was inaccessible from this cloud instance; verification was not bypassed.

From the repository root, using your actual downloaded paths, authoritative URL, and hashes:

```bat
py -3.12 -m scripts.prepare_ffmpeg --archive C:\downloads\ffmpeg-static.zip --sha256 PUBLISHER_BINARY_SHA256 --source-url https://publisher.example/exact-build.zip --source-archive C:\downloads\ffmpeg-source.zip --source-sha256 PUBLISHER_SOURCE_SHA256
```

The command checks both archive hashes before importing into ignored `assets/`, records provenance, and refuses to overwrite existing assets. Review the exact source contents and license for your selected build. Source provenance and notices travel with the distribution. It does not download or execute unverified binaries.

## Build the portable Windows EXE

On Windows with **Python 3.12.7 x64**, Tcl/Tk, and prepared assets:

```bat
BUILD_WINDOWS_EXE.bat
```

This creates `.venv-build`, installs pinned dependencies, checks asset hashes, runs tests, builds a **windowed one-folder** EXE with **PyInstaller 6.14.1**, and collects dependency/runtime licenses. Output: `dist\VideoDownloader\VideoDownloader.exe`. A frozen worker uses a private event file, so progress does not depend on a console being present. Heavy extractor imports occur in the download worker, keeping GUI startup lightweight.

The packaging method follows the Toyota CYD35 related application's [documented Windows 1607 validation](https://github.com/jafinch78/Toyota-Hybrid-CYD35-Diagnostic-CAN-Logger/blob/main/docs/releases/video-narration-transcriber-v1.0.5/VALIDATION.md). That record validates that other application, not this downloader's new dependency combination.

## Native Windows 1607 release checks

Run on **native Windows 10 x64 version 1607 build 14393**:

```bat
RELEASE_CHECKLIST_WIN1607.bat
```

The automated check rejects other OS builds, runs the actual frozen EXE's diagnostic mode, generates separate audio/video streams, serves them locally, downloads/merges them through the frozen worker, checks both streams, and records runtime versions and hashes in `dist\validation-win1607.json`. Windows build tooling/Python can be present for this automated harness; that does not establish no-Python startup on the destination machine.

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
