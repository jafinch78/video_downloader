# Third-party software

The portable distribution includes license texts collected from the installed pinned dependencies under `third-party-licenses`, plus the selected FFmpeg build's license, source ZIP, and provenance manifest under `_internal/assets`.

- Python 3.12.7: Python Software Foundation license and included notices.
- Tcl/Tk: upstream Tcl/Tk license texts from the Windows Python installation.
- yt-dlp: Unlicense; some included extractor code has its own notices. Preserve the complete installed license directory.
- yt-dlp-ejs, Brotli, certifi, charset-normalizer, idna, mutagen, PyCryptodome, requests, urllib3, websockets: retain their exact installed license texts. In particular, certifi uses MPL-2.0 and mutagen uses GPL-2.0-or-later. Review the applicable source-distribution obligations before sharing the bundle.
- FFmpeg/FFprobe: license depends on the selected build and enabled components. Do not infer LGPL or GPL solely from the executable name. Bundle the build's actual license and corresponding source/build/dependency sources. A publisher checksum verifies archive identity; it does not certify compatibility or completeness of source obligations.
- PyInstaller 6.14.1: GPL with its bootloader distribution exception; see https://pyinstaller.org/en/stable/license.html. Build tooling is not installed on the end user's machine.

Authoritative sources: https://www.python.org/ ; https://www.tcl.tk/ ; https://github.com/yt-dlp/yt-dlp ; https://ffmpeg.org/ ; https://pyinstaller.org/ . Dependency metadata and the included license texts control if this overview differs.
