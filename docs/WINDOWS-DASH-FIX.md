# Windows DASH fixture path repair

The uploaded Windows 10 build 14393 report confirms Python 3.12.7 x64, all 11 pinned runtime-package imports, native Brotli/AES, certificate data, Tcl/Tk 8.6.13, FFmpeg 6.1.1 and FFprobe 6.1.1 passed their local checks. The build then stops in `test_separate_streams_are_merged` with an HTTP 404. It has not reached PyInstaller.

The fixture passes an absolute native Windows path to FFmpeg's DASH muxer. FFmpeg 6.1.1 `libavformat/dashenc.c` lines 1460–1466 derive the output directory using the final `/` character. A Windows path containing backslashes yields an empty muxer directory, so generated fragment files land in the process working directory while the manifest is written in the fixture directory. The local HTTP server serves only the fixture directory and cannot find those fragments.

Both the integration fixture and the later frozen-bundle smoke fixture now pass only the manifest basename and explicitly set the FFmpeg subprocess working directory to the HTTP-served media directory. They also verify that initialization files and audio/video fragments are present there before downloading. The real separate-stream download/merge assertion remains enabled.

Apply `VideoDownloader-dash-path-fix.zip` by replacing these two files in the existing source folder:

- `tests/test_integration.py`
- `scripts/bundle_check.py`

Keep the previous `scripts/build_support.py` repair, downloaded `assets` and `.venv-build`. Rerun `BUILD_WINDOWS_EXE.bat`; no package or media-asset reinstall is needed unless integrity checks identify a separate problem. Local checks pass, but the Windows rerun and eventual frozen-bundle checks still determine native readiness.
