import hashlib
import io
import json
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from scripts import build_support as support

class BootstrapTests(unittest.TestCase):
    def archives(self, root):
        binary=root/'binary.zip'
        with zipfile.ZipFile(binary,'w') as archive:
            archive.writestr('vendor/bin/ffmpeg.exe',b'MZ-ffmpeg-fixture')
            archive.writestr('vendor/bin/ffprobe.exe',b'MZ-ffprobe-fixture')
            archive.writestr('vendor/LICENSE',b'GPL fixture license')
        source=root/'source.tar.gz'
        data=b'/* actual source fixture */'
        with tarfile.open(source,'w:gz') as archive:
            member=tarfile.TarInfo('FFmpeg-n6.1.1/fftools/ffmpeg.c')
            member.size=len(data)
            archive.addfile(member,io.BytesIO(data))
        return binary,source

    def specs(self,binary,source):
        return patch.multiple(support,
            FFMPEG_URL='https://example.com/binary.zip',
            FFMPEG_SHA256=hashlib.sha256(binary.read_bytes()).hexdigest(),
            SOURCE_URL='https://example.com/source.tar.gz',
            SOURCE_SHA512=hashlib.sha512(source.read_bytes()).hexdigest())

    def test_missing_manifest_prepares_verified_cached_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            cache=root/'cache';cache.mkdir()
            binary,source=self.archives(cache)
            with self.specs(binary,source):
                support.ensure_assets(root/'assets',cache)
                manifest=support.validate_assets(root/'assets')
                self.assertEqual(manifest['archive_sha256'],hashlib.sha256(binary.read_bytes()).hexdigest())
                with zipfile.ZipFile(root/'assets/ffmpeg-source.zip') as archive:
                    self.assertIn('FFmpeg-n6.1.1/fftools/ffmpeg.c',archive.namelist())
                with patch.object(support,'_download_verified',side_effect=AssertionError('must reuse existing verified assets')):
                    support.ensure_assets(root/'assets',cache)

    def test_wrong_download_checksum_never_creates_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch.object(support.urllib.request,'urlopen',return_value=io.BytesIO(b'tampered')):
                with self.assertRaisesRegex(ValueError,'checksum'):
                    support._download_verified('https://example.com/archive.zip',root/'cache','0'*64,'sha256')
            self.assertFalse((root/'cache/archive.zip').exists())

    def test_existing_user_assets_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            assets=root/'assets';assets.mkdir()
            (assets/'mine.txt').write_text('preserve me')
            with self.assertRaisesRegex(ValueError,'overwrite'):
                support.ensure_assets(assets,root/'cache')
            self.assertEqual((assets/'mine.txt').read_text(),'preserve me')
