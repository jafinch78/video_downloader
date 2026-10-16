"""Resolve bundled tools without depending on the working directory."""
import os
import shutil
import sys
from pathlib import Path


def asset_path(name: str) -> Path:
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
    return root / 'assets' / name


def media_tool(name: str) -> str:
    filename = name + ('.exe' if os.name == 'nt' else '')
    bundled = asset_path(filename)
    if bundled.is_file():
        return str(bundled)
    if not getattr(sys, 'frozen', False):
        found = shutil.which(name)
        if found:
            return found
    raise RuntimeError(f'Missing {filename}. Restore the complete portable application folder.')


def subprocess_options() -> dict:
    if os.name == 'nt':
        return {'creationflags': 0x08000000}  # CREATE_NO_WINDOW
    return {}


def worker_command(url: str, destination: Path) -> list[str]:
    prefix = [sys.executable, '--worker'] if getattr(sys, 'frozen', False) else [sys.executable, '-m', 'video_downloader.worker']
    return prefix + ['--url', url, '--destination', str(destination)]
