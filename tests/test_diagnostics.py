import json
import tempfile
import unittest
from pathlib import Path
from video_downloader.diagnostics import write_diagnostic

class DiagnosticTests(unittest.TestCase):
    def test_diagnostic_runs_tools_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'runtime.json'
            write_diagnostic(output)
            result=json.loads(output.read_text())
            self.assertIn('ffmpeg version',result['ffmpeg'])
            self.assertIn('ffprobe version',result['ffprobe'])
            self.assertEqual(result['bits'],64)
            self.assertFalse(result['frozen'])

    def test_all_pinned_dependencies_are_loaded_and_exercised(self):
        from video_downloader.diagnostics import check_dependencies
        from unittest.mock import patch
        result=check_dependencies()
        self.assertEqual(len(result['packages']),11)
        self.assertTrue(all(item['passed'] for item in result['packages']))
        self.assertTrue(result['tls_certificates'])
        self.assertTrue(result['native_brotli'])
        self.assertTrue(result['native_crypto'])
        with patch('video_downloader.diagnostics.version', return_value='wrong'):
            with self.assertRaises(RuntimeError):
                check_dependencies()

    def test_failed_check_writes_failure_report(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'dependencies.json'
            with patch('video_downloader.diagnostics.version',return_value='wrong'):
                with self.assertRaises(RuntimeError):
                    write_diagnostic(output)
            result=json.loads(output.read_text())
            self.assertFalse(result['passed'])
            self.assertIn('expected',result['error'])

    def test_dependency_inventory_matches_lockfile(self):
        from video_downloader.dependencies import PACKAGES
        locked={line.split('==')[0]:line.split('==')[1] for line in Path('requirements-lock.txt').read_text().splitlines() if line}
        self.assertEqual({name:pin for name,pin,module in PACKAGES},locked)

    def test_frozen_check_rejects_external_dependency_fallback(self):
        from unittest.mock import patch
        from video_downloader.diagnostics import check_dependencies
        with patch('sys.frozen',True,create=True), patch('sys._MEIPASS','/a/nonexistent/bundle',create=True):
            with self.assertRaisesRegex(RuntimeError,'outside the portable package'):
                check_dependencies()
