"""Release prerequisites shared by the build and native checklist."""
import hashlib
import json
import platform
import struct
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def require_release_runtime(version=None, system=None, bits=None):
    version = tuple(version or sys.version_info[:3])
    system = system or platform.system()
    bits = bits or struct.calcsize('P') * 8
    if version != (3, 12, 7) or system != 'Windows' or bits != 64:
        raise ValueError('Build requires Windows and Python 3.12.7 x64, including Tcl/Tk.')


def validate_assets(root: Path) -> dict:
    try:
        manifest = json.loads((root/'manifest.json').read_text(encoding='utf-8'))
        required = {'ffmpeg.exe', 'ffprobe.exe', 'FFmpeg-LICENSE.txt', 'ffmpeg-source.zip'}
        if not required <= manifest['files'].keys():
            raise ValueError('Required media tools, license, or corresponding source are missing.')
        if not manifest['archive_url'].startswith('https://') or len(manifest['archive_sha256']) != 64:
            raise ValueError('Missing upstream archive provenance.')
        for name in required:
            path = root/name
            if not path.is_file() or path.stat().st_size == 0 or sha256(path) != manifest['files'][name]:
                raise ValueError(f'Asset is missing or its hash differs: {name}')
        for name in ('ffmpeg.exe', 'ffprobe.exe'):
            with (root/name).open('rb') as stream:
                if stream.read(2) != b'MZ':
                    raise ValueError(f'Not a Windows executable: {name}')
        return manifest
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError('Prepare verified FFmpeg assets first; see README.md.') from exc


if __name__ == '__main__':
    require_release_runtime()
    validate_assets(Path(__file__).resolve().parents[1]/'assets')
