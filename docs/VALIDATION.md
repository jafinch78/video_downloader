# Development validation — 2026-10-16

## Verified in this machine

Linux x64, Python 3.12.14, Tk 9.0, FFmpeg/FFprobe 7.1.5, yt-dlp 2026.8.19. Full suite uses a virtual display from a signature-verified Debian Xvfb package extracted under the checkout's ignored `.cloud-tools` folder.

Command: `DISPLAY=:98 .venv/bin/python -m unittest discover -v`.

Result after review fixes: **33 tests passed; zero failures or skips**. Includes real local HTTP downloads, distinct audio/video DASH merging, probing both streams, silent-source rejection, repeated download preservation, actual worker process/file-event transport, GUI controls, source diagnostics, asset hash validation, and packaging layout/checksums. `pip check` found no broken requirements. Windows x64 Python 3.12 dependency wheels resolved/downloaded successfully; this does not prove runtime compatibility.

The cloud installation script was executed twice successfully. The saved startup instructions' retained Xvfb and GUI test commands were executed successfully on display :98. Installation and startup instructions were saved to the environment configuration draft; this does not publish a snapshot.

## Independent review and fixes

An independent reviewer inspected application and build code at 313dd0c. Three Important findings were reproduced with real failing tests before fixing:

- Signed URL query values leaked through yt-dlp's generic extractor IDs. External extractor errors/warnings now use controlled message categories; full-URL redaction is case-insensitive. Real refused-connection and uppercase-redaction regressions pass.
- Generic multi-video pages downloaded entries before rejecting the playlist. A metadata preflight now rejects playlist/multi-video results before processing media; the regression asserts neither media endpoint was requested.
- Concurrent application instances shared partial files. A nonblocking OS file lock now owns each staging folder for the entire download/verify/publish sequence. OS closure releases ownership on process termination, and the lock inode is retained to prevent unlink races. The concurrent real-download regression passes without corrupted staging.

An initial combined GUI/process test run crashed with Tcl_AsyncDelete when destroyed Tk test objects were collected on a later worker thread. Test teardown now explicitly releases and collects Tk objects on the main thread; full runs pass.

## Decisions

- Used the existing isolated `work` checkout instead of creating another worktree; cloud tasks already provide isolation. The local ledger substitutes for cloud-skill helper scripts that are not exposed as executable filesystem paths. Cost if isolation were wrong: edits could share a user's checkout; the initial checkout was inspected and empty.
- Used private JSON-lines event files instead of relying on stdout, because a windowed frozen process can have `sys.stdout=None`. Cost if wrong: frozen progress/results could fail; a no-stdout test and the reviewer's real no-stdout/no-stderr download check passed. Native frozen testing remains required.
- Did not fabricate a Windows EXE or use unverified Windows media binaries. Cost: the requested release artifact still requires an external Windows build and native validation.

## Deferred minor findings

- A narrow GUI poll/terminal-event race can enable Download before the previous terminal event is rendered, briefly displaying stale completion progress for a new job.
- Source launch requires the documented repository working directory: an absolute run_gui.py launch elsewhere does not supply the package path to its child worker. The frozen EXE is independent of the current directory.
- Windows taskkill nonzero return status is not explicitly handled; the native cancellation failure path remains to be tested.
- The native OS gate checks Windows build 14393 but does not distinguish Windows Server 2016 from Windows 10 workstation. Run the checklist on the explicitly required Windows 10 machine.

## Unrun release gates and external prerequisites

**No Windows EXE was built. No Windows 10 1607 compatibility is certified.** No native Windows runner is available in this environment, and no verified Windows 1607 FFmpeg/FFprobe build was supplied. Gyan's distribution host returned proxy 403; verification was not bypassed. BtbN's current README guarantees only Windows 10 22H2, so current builds cannot be presumed compatible with 1607.

Build and validate on Windows using README.md and the supplied scripts. Check no-Python/offline GUI startup, real supported-site extraction, playback, Unicode paths, failure recovery, and cancellation during merging on build 14393. The generated release checklist records artifact hashes and distinguishes automated checks from manually attested checks.

No third-party live website download was run: such checks are optional and would not establish universal site support. No release was pushed or published. All source commits currently exist only in this checkout; fresh-task restoration of local-only commits has not been independently verified. The source ZIP provides a separate portable copy of the code.
