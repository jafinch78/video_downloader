import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from scripts.prepare_ffmpeg import prepare
from scripts.release_check import require_native_target

class BuildToolTests(unittest.TestCase):
    def test_prepare_verifies_archive_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            binary=root/'binary.zip'
            with zipfile.ZipFile(binary,'w') as archive:
                archive.writestr('ffmpeg/bin/ffmpeg.exe',b'MZffmpeg')
                archive.writestr('ffmpeg/bin/ffprobe.exe',b'MZffprobe')
                archive.writestr('ffmpeg/LICENSE.txt',b'License text')
            source=root/'source.zip'
            with zipfile.ZipFile(source,'w') as archive:
                archive.writestr('source/README','Source distribution')
            sha=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
            dest=root/'assets'
            with self.assertRaises(ValueError):
                prepare(binary,'0'*64,'https://example.com/build.zip',source,sha(source),dest)
            self.assertFalse(dest.exists())
            prepare(binary,sha(binary),'https://example.com/build.zip',source,sha(source),dest)
            manifest=json.loads((dest/'manifest.json').read_text())
            self.assertEqual(manifest['files']['ffmpeg.exe'],hashlib.sha256(b'MZffmpeg').hexdigest())
            with self.assertRaises(FileExistsError):
                prepare(binary,sha(binary),'https://example.com/build.zip',source,sha(source),dest)

    def test_native_target(self):
        require_native_target('Windows',14393)
        for system,build in [('Linux',14393),('Windows',19045)]:
            with self.assertRaises(ValueError):
                require_native_target(system,build)
