import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from video_downloader.controller import DownloadController

class ControllerTests(unittest.TestCase):
    def run_worker(self, code):
        controller = DownloadController()
        with patch('video_downloader.controller.worker_command', return_value=[sys.executable, '-c', code]):
            controller.start('https://example.com', Path('/tmp'))
        return controller

    def wait_events(self, controller):
        events=[]
        deadline=time.monotonic()+8
        while controller.active and time.monotonic()<deadline:
            events.extend(controller.poll())
            time.sleep(.02)
        events.extend(controller.poll())
        self.assertFalse(controller.active)
        return events

    def test_completion_waits_for_successful_exit(self):
        c=self.run_worker('print(\'{"type":"complete","path":"movie.mp4"}\', flush=True); raise SystemExit(1)')
        events=self.wait_events(c)
        self.assertFalse(any(e['type']=='complete' for e in events))
        self.assertTrue(any(e['type']=='error' for e in events))

    def test_success(self):
        events=self.wait_events(self.run_worker('print(\'{"type":"complete","path":"movie.mp4"}\')'))
        self.assertEqual(events[-1]['type'], 'complete')

    def test_malformed_or_missing_completion(self):
        for code in ['print("junk")', 'print("[]")', 'pass']:
            events=self.wait_events(self.run_worker(code))
            self.assertEqual(events[-1]['type'], 'error')

    def test_cancel_and_prevent_double_start(self):
        c=self.run_worker('import time; time.sleep(60)')
        with self.assertRaises(RuntimeError):
            c.start('https://example.com', Path('/tmp'))
        began=time.monotonic()
        c.cancel()
        self.assertLess(time.monotonic()-began, .5)
        events=self.wait_events(c)
        self.assertEqual(events[-1]['type'], 'cancelled')

    @unittest.skipIf(os.name=='nt', 'POSIX process group check; Windows tree checked natively')
    def test_cancel_descendant(self):
        with tempfile.TemporaryDirectory() as directory:
            marker=Path(directory)/'escaped'
            child=f'import time; from pathlib import Path; time.sleep(1); Path({str(marker)!r}).touch()'
            c=self.run_worker(f'import subprocess,sys,time; subprocess.Popen([sys.executable,"-c",{child!r}]); print(\'{{"type":"status","message":"ready"}}\',flush=True); time.sleep(60)')
            deadline=time.monotonic()+4
            while time.monotonic()<deadline:
                if c.poll():
                    break
                time.sleep(.02)
            c.cancel()
            self.wait_events(c)
            time.sleep(1.2)
            self.assertFalse(marker.exists())
