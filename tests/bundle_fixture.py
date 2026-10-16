"""Structural fixtures only: deliberately not executable Windows programs."""
import hashlib
import json
from pathlib import Path
from scripts.verify_delivery import REQUIRED


def create_bundle(root: Path):
    for relative in REQUIRED:
        path=root/relative
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(b'MZ-test-fixture-not-runnable' if path.suffix in ('.exe','.dll') else b'test fixture')
    assets=root/'_internal/assets'
    names=('ffmpeg.exe','ffprobe.exe','FFmpeg-LICENSE.txt','ffmpeg-source.zip')
    manifest={'archive_url':'https://example.com/test-fixture.zip','archive_sha256':'a'*64,
              'files':{name:hashlib.sha256((assets/name).read_bytes()).hexdigest() for name in names}}
    (assets/'manifest.json').write_text(json.dumps(manifest))
    licenses=root/'third-party-licenses'
    licenses.mkdir()
    (licenses/'test.txt').write_text('fixture license')
    return root
