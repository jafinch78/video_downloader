import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from scripts.package_release import package_release
from tests.bundle_fixture import create_bundle
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
            create_bundle(app)
            report=root/'smoke.json'
            from video_downloader.dependencies import PACKAGES
            runtime={'frozen':True,'passed':True,'python':'3.12.7','bits':64,'tkinter':{'passed':True},'dependencies':{'packages':[{'name':name,'version':pin,'passed':True} for name,pin,module in PACKAGES]}}
            report.write_text(json.dumps({'automated_pass':True,'exe_sha256':hashlib.sha256((app/'VideoDownloader.exe').read_bytes()).hexdigest(),'runtime':runtime,'bundle_files':{p.relative_to(app).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in app.rglob('*') if p.is_file()}}))
            archive=package_release(app,root/'out',smoke_report=report)
            with zipfile.ZipFile(archive) as z:
                self.assertIn('VideoDownloader/VideoDownloader.exe',z.namelist())
            digest=hashlib.sha256(archive.read_bytes()).hexdigest()
            self.assertIn(digest,archive.with_suffix('.zip.sha256').read_text())

    def test_packaging_rejects_missing_or_stale_executable_smoke(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            app=create_bundle(root/'VideoDownloader')
            report=root/'smoke.json'
            with self.assertRaises(ValueError):
                package_release(app,root/'out',smoke_report=report)
            report.write_text(json.dumps({'automated_pass':True,'exe_sha256':'wrong'}))
            with self.assertRaises(ValueError):
                package_release(app,root/'out',smoke_report=report)
            self.assertFalse((root/'out').exists())

    def test_packaging_rejects_changed_dependency_after_smoke(self):
        from video_downloader.dependencies import PACKAGES
        for changed in ['_internal/python312.dll','_internal/certifi/cacert.pem']:
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as directory:
                root=Path(directory)
                app=create_bundle(root/'VideoDownloader')
                cert=app/'_internal/certifi/cacert.pem'
                cert.parent.mkdir(parents=True,exist_ok=True)
                cert.write_bytes(b'certificate fixture')
                runtime={'frozen':True,'passed':True,'python':'3.12.7','bits':64,'tkinter':{'passed':True},'dependencies':{'packages':[{'name':name,'version':pin,'passed':True} for name,pin,module in PACKAGES]}}
                report=root/'smoke.json'
                report.write_text(json.dumps({'automated_pass':True,'exe_sha256':hashlib.sha256((app/'VideoDownloader.exe').read_bytes()).hexdigest(),'runtime':runtime,'bundle_files':{p.relative_to(app).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in app.rglob('*') if p.is_file()}}))
                (app/changed).write_bytes(b'MZ-replaced-after-smoke')
                with self.assertRaises(ValueError):
                    package_release(app,root/'out',smoke_report=report)
