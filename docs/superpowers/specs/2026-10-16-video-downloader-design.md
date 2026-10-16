# Portable Windows video downloader

## Agreed outcome

Create a standalone desktop GUI that accepts a typed or pasted website/video URL and downloads one video, including its audio, to a user-selected local folder. Target Windows 10 version 1607 x64 (build 14393). The user approved following the packaging method documented by the Toyota CYD35 related applications.

Offline standalone means no installed Python runtime, package installation, or cloud service is required to launch the distributed application. Fetching website content requires internet access. Supported websites depend on the bundled extractor version; universal website support is not promised.

## Toolchain and distribution

Use Python 3.12.7 x64 and Tkinter, frozen on Windows with PyInstaller 6.14.1 into a portable folder containing the GUI EXE, its runtime dependencies, and FFmpeg/FFprobe. Distribute this folder as a ZIP. Users extract the complete folder and launch the EXE without installing Python. A single-file EXE and VC140 C++ implementation are outside this version.

Reference: Toyota-Hybrid-CYD35-Diagnostic-CAN-Logger, docs/releases/video-narration-transcriber-v1.0.5/VALIDATION.md. That application documents this Python/PyInstaller combination and successful native Windows 1607 testing. Its success does not establish compatibility of this downloader or its new dependencies.

Select and pin yt-dlp and build dependencies during implementation. Bundle a Windows x64 FFmpeg build whose provenance, checksum, redistribution license, and Windows 1607 compatibility are checked. Preserve TLS verification. Include required third-party notices. Dependencies are bundled at build time; the installed app performs no automatic dependency installation or self-update. Website changes may require a new application release. Some extractors require additional JavaScript runtimes or external services; these are outside this initial bundle and must produce an actionable unsupported-requirement error.

## User interface and behavior

One window contains a URL entry, a destination folder entry with Browse, Download and Cancel buttons, a progress bar, and a scrolling status area. Default destination is the user's Downloads folder if it exists, otherwise the home folder. Validate an HTTP/HTTPS URL and a writable destination before beginning. Do not interpret input as shell commands. Process a single video per action; do not download playlists.

Select the best available video and audio, or a combined stream when appropriate. Prefer MP4-compatible streams and merge without re-encoding. If the selected streams cannot be combined into MP4 without conversion, use MKV and report the actual output path. Preserve video quality rather than performing a potentially expensive transcode. Success requires a completed final media file with both video and audio; videos with no available audio fail with a clear explanation. Never report success from download percentage alone.

Use a sanitized title and media ID for filenames. Do not overwrite existing completed files. Preserve resumable partial downloads on cancellation or failure, and explain this in status output. Do not delete unrelated files. Show progress and the final file path, with clear errors for unsupported sites, inaccessible media, missing audio, networking, permission, disk, and merge failures.

## Components and execution

- GUI: Tkinter widgets and a main-thread event queue. Only the main thread updates widgets.
- Controller: one active download, progress events, cancellation, and completion state.
- Worker: a separate process running the bundled downloader module with yt-dlp and bundled media tools. A subprocess isolates downloads and permits cancellation while extraction or merging is blocked.
- Runtime paths: resolve bundled assets in frozen mode and developer dependencies in source mode without depending on the current directory.
- Packaging: Windows build script, pinned requirements, PyInstaller configuration, and a native release checklist.

Launch subprocesses with argument lists and no shell, hiding console windows on Windows. Cancellation terminates the worker and its FFmpeg descendants, waits for cleanup, and restores the GUI to idle. Closing during a download asks whether to cancel and exit. Communication uses structured progress/status events; diagnostics redact URL credentials and query strings. No credentials are saved by the app.

## Scope

Include public HTTP/HTTPS media supported by the bundled yt-dlp and direct media URLs. Exclude DRM decryption, browser-cookie import, login management, playlists, batch queues, conversion profiles, and automatic updates. No external server, database, or subscription is needed.

## Verification and release gates

Automated tests cover URL and destination validation, format/audio selection, event handling, cancellation, filenames, error propagation, and frozen asset resolution. A local HTTP fixture and generated audio/video exercise real downloading and merging with FFmpeg/FFprobe, verifying the final file's streams and cancellation cleanup without relying on third-party website uptime. GUI launch and interaction are checked with a display where available.

Build the actual Windows artifact on Windows using the pinned toolchain. On native Windows 10 1607 x64 build 14393, launch the extracted package without installed Python or a network connection to verify startup, then download a controlled audio/video fixture online, verify both streams and playback, test cancellation, and test a destination containing spaces and non-ASCII characters. Record artifact hashes, OS/build, dependency versions, and results. An optional supported-site smoke test assesses extraction separately from the controlled fixture.

The current development machine is Linux with Python 3.12.14 and FFmpeg. Linux tests can validate portable application logic and media integration; they cannot certify the Windows EXE or Windows 1607 compatibility. A Windows build and native test remain release prerequisites unless a suitable runner becomes available.

## Deliverables

Application source, automated tests and fixtures, pinned development/build requirements, Windows build and release-check scripts, user/build documentation, and third-party licensing information. Supply a portable Windows release ZIP only after an actual Windows build; mark any unexecuted native checks explicitly. Keep work in the existing isolated checkout; no additional worktree is needed.
