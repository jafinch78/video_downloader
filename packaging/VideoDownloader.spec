# Build on Windows using Python 3.12.7 x64 and PyInstaller 6.14.1.
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, copy_metadata

root = Path(SPECPATH).parent
assets = root / 'assets'
ytdlp_data, ytdlp_binaries, ytdlp_imports = collect_all('yt_dlp')
a = Analysis([str(root/'run_gui.py')], pathex=[str(root)],
    binaries=ytdlp_binaries + [(str(assets/'ffmpeg.exe'), 'assets'), (str(assets/'ffprobe.exe'), 'assets')],
    datas=ytdlp_data + copy_metadata('yt-dlp', recursive=True) + [
        (str(assets/'manifest.json'), 'assets'),
        (str(assets/'FFmpeg-LICENSE.txt'), 'assets'),
        (str(assets/'ffmpeg-source.zip'), 'assets'),
    ],
    hiddenimports=ytdlp_imports + ['video_downloader.worker', 'video_downloader.diagnostics'],
    hookspath=[], runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='VideoDownloader',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=False,
    disable_windowed_traceback=False, target_arch='x86_64')
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='VideoDownloader')
