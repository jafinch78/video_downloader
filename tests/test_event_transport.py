import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from video_downloader.worker import main

class EventTransportTests(unittest.TestCase):
    def test_windowed_worker_reports_without_stdout(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'events.jsonl'
            with patch.dict(os.environ, {'VIDEO_DOWNLOADER_EVENTS':str(path)}), patch('sys.stdout',None):
                result=main(['--url','bad-url','--destination',directory])
            self.assertEqual(result,1)
            self.assertEqual(json.loads(path.read_text())['type'],'error')
