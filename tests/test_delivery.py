import unittest
from pathlib import Path
from scripts.verify_delivery import verify_folder, verify_zip

class DeliveryTests(unittest.TestCase):
    def test_source_archive_is_not_an_application_distribution(self):
        import tempfile
        import zipfile
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'source.zip'
            with zipfile.ZipFile(source,'w') as archive:
                archive.write('run_gui.py','VideoDownloader-source/run_gui.py')
            with self.assertRaisesRegex(ValueError,'VideoDownloader.exe'):
                verify_zip(source)

    def test_missing_built_folder_is_not_a_deliverable(self):
        with self.assertRaisesRegex(ValueError,'VideoDownloader.exe'):
            verify_folder(Path('dist/does-not-exist'))

    def test_missing_bundle_fails_and_retains_failure_json(self):
        import json
        import subprocess
        import sys
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            report=root/'bundle.json'
            result=subprocess.run([sys.executable,'-m','scripts.bundle_check','--exe',str(root/'VideoDownloader.exe'),'--report',str(report)],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            status=json.loads(report.read_text())
            self.assertFalse(status['automated_pass'])
            self.assertFalse(status['release_ready'])
            self.assertIn('missing VideoDownloader.exe',status['error'])
