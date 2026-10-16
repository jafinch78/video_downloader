import functools
import http.server
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from video_downloader.worker import run_download

class MediaIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='video fixture 空 ')
        self.root = Path(self.temp.name)
        self.output = self.root/'output 空'
        self.output.mkdir()
        class Quiet(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass
        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=self.temp.name))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def media(self, filename, audio=True):
        command = ['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=size=64x64:rate=10:duration=1']
        if audio:
            command += ['-f', 'lavfi', '-i', 'sine=frequency=440:duration=1']
        command += ['-c:v', 'libx264']
        if audio:
            command += ['-c:a', 'aac', '-shortest']
        subprocess.run(command + [str(self.root/filename)], check=True, capture_output=True)
        return f'http://127.0.0.1:{self.server.server_port}/{filename}'

    def test_download_and_repeat_preserves_existing(self):
        url = self.media('sample.mp4')
        events = []
        first = run_download(url, self.output, events.append)
        self.assertTrue(first.is_file())
        self.assertEqual(events[-1]['type'], 'complete')
        original = first.read_bytes()
        second = run_download(url, self.output, events.append)
        self.assertNotEqual(first, second)
        self.assertEqual(first.read_bytes(), original)
        self.assertEqual(second.read_bytes(), original)

    def test_silent_video_never_completes(self):
        url = self.media('silent.mp4', audio=False)
        events = []
        with self.assertRaises(Exception):
            run_download(url, self.output, events.append)
        self.assertFalse(any(e['type']=='complete' for e in events))
        self.assertFalse(list(self.output.glob('*.mp4')))
