import functools
import http.server
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from video_downloader.worker import run_download

class MediaIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='video fixture 空 ')
        self.root = Path(self.temp.name)
        self.output = self.root/'output 空'
        self.output.mkdir()
        self.requests=[]
        requests=self.requests
        class Quiet(http.server.SimpleHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path.split('?')[0])
                if self.path.split('?')[0]=='/concurrent.mp4':
                    time.sleep(.2)
                return super().do_GET()
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
        command += ['-c:v', 'mpeg4']
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

    def test_separate_streams_are_merged(self):
        manifest=self.root/'split.mpd'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=size=64x64:rate=10:duration=1',
                        '-f','lavfi','-i','sine=frequency=440:duration=1','-c:v','mpeg4','-c:a','aac',
                        '-shortest','-f','dash',str(manifest)], check=True, capture_output=True)
        events=[]
        final=run_download(f'http://127.0.0.1:{self.server.server_port}/split.mpd',self.output,events.append)
        self.assertTrue(final.is_file())
        self.assertTrue(any('Combining' in e.get('message','') for e in events))
        self.assertEqual(events[-1]['type'], 'complete')

    def test_controller_runs_real_worker(self):
        from video_downloader.controller import DownloadController
        controller=DownloadController()
        controller.start(self.media('controlled.mp4'),self.output)
        events=[]
        deadline=time.monotonic()+15
        while controller.active and time.monotonic()<deadline:
            events.extend(controller.poll())
            time.sleep(.02)
        events.extend(controller.poll())
        if controller.active:
            controller.cancel()
        self.assertFalse(controller.active, 'worker did not finish')
        self.assertEqual(events[-1]['type'],'complete', events)
        self.assertTrue(Path(events[-1]['path']).is_file())

    def test_multi_video_page_is_rejected_before_media_download(self):
        self.media('first.mp4')
        (self.root/'second.mp4').write_bytes((self.root/'first.mp4').read_bytes())
        (self.root/'multiple.html').write_text('<html><title>Multiple</title><video src="first.mp4"></video><video src="second.mp4"></video></html>')
        with self.assertRaisesRegex(RuntimeError,'one video'):
            run_download(f'http://127.0.0.1:{self.server.server_port}/multiple.html',self.output,lambda e:None)
        self.assertNotIn('/first.mp4',self.requests)
        self.assertNotIn('/second.mp4',self.requests)

    def test_signed_url_failure_never_leaks_query(self):
        import os
        import json
        from unittest.mock import patch
        from video_downloader.worker import main
        events=self.root/'events.jsonl'
        import socket
        with socket.socket() as probe:
            probe.bind(('127.0.0.1',0))
            port=probe.getsockname()[1]
        url=f'http://127.0.0.1:{port}/video?token=VERY_PRIVATE'
        with patch.dict(os.environ,{'VIDEO_DOWNLOADER_EVENTS':str(events)}):
            self.assertEqual(main(['--url',url,'--destination',str(self.output)]),1)
        result=events.read_text()
        self.assertNotIn('VERY_PRIVATE',result)
        self.assertNotIn('token=',result)
        self.assertEqual(json.loads(result.splitlines()[-1])['type'],'error')

    def test_concurrent_same_url_has_exclusive_stage(self):
        from concurrent.futures import ThreadPoolExecutor
        url=self.media('concurrent.mp4')
        def attempt():
            try:
                return run_download(url,self.output,lambda e:None)
            except Exception as exc:
                return exc
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda n:attempt(),range(2)))
        self.assertEqual(sum(isinstance(r,Path) for r in results),1,results)
        errors=[str(r) for r in results if isinstance(r,Exception)]
        self.assertEqual(len(errors),1)
        self.assertIn('already being downloaded',errors[0])
