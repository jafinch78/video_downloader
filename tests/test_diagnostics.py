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
