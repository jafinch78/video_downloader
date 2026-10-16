import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from scripts.package_release import package_release
from scripts.build_support import validate_assets, require_release_runtime

class PackagingTests(unittest.TestCase):
    def test_assets_require_integrity_and_notices(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with self.assertRaises(ValueError):
                validate_assets(root)
            files={}
            for name,data in [('ffmpeg.exe',b'MZtest'),('ffprobe.exe',b'MZtest'),('FFmpeg-LICENSE.txt',b'License'),('ffmpeg-source.zip',b'source')]:
                (root/name).write_bytes(data)
                files[name]=hashlib.sha256(data).hexdigest()
            (root/'manifest.json').write_text(json.dumps({'files':files,'archive_url':'https://example.com/ffmpeg.zip','archive_sha256':'a'*64}))
            validate_assets(root)
            (root/'ffprobe.exe').write_bytes(b'tampered')
            with self.assertRaises(ValueError):
                validate_assets(root)

    def test_runtime_rejects_wrong_version_or_platform(self):
        for version,system,bits in [((3,12,14),'Windows',64),((3,12,7),'Linux',64),((3,12,7),'Windows',32)]:
            with self.assertRaises(ValueError):
                require_release_runtime(version,system,bits)
        require_release_runtime((3,12,7),'Windows',64)

    def test_zip_layout_and_hash(self):
        with tempfile.TemporaryDirectory(prefix='release 空 ') as directory:
            root=Path(directory)
            app=root/'VideoDownloader'
            app.mkdir()
            with self.assertRaises(ValueError):
                package_release(app,root/'out')
            (app/'VideoDownloader.exe').write_bytes(b'MZexe')
            (app/'README.txt').write_text('Read me')
            archive=package_release(app,root/'out')
            with zipfile.ZipFile(archive) as z:
                self.assertIn('VideoDownloader/VideoDownloader.exe',z.namelist())
            digest=hashlib.sha256(archive.read_bytes()).hexdigest()
            self.assertIn(digest,archive.with_suffix('.zip.sha256').read_text())
