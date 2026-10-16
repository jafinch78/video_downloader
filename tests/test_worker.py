import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from video_downloader.worker import download_options, verify_media, publish, progress_event

class WorkerTests(unittest.TestCase):
    def test_options(self):
        opts = download_options(Path('/tmp/out'), lambda e: None)
        self.assertTrue(opts['noplaylist'])
        self.assertFalse(opts.get('nocheckcertificate', False))
        self.assertTrue(opts['nooverwrites'])
        self.assertIn('acodec', opts['format'])
        self.assertIn('mkv', opts['merge_output_format'])

    def test_progress(self):
        self.assertEqual(progress_event({'downloaded_bytes': 25, 'total_bytes': 100})['percent'], 25)
        self.assertIsNone(progress_event({})['percent'])
        self.assertEqual(progress_event({'downloaded_bytes': 200, 'total_bytes': 100})['percent'], 100)

    def test_verify_requires_both_streams(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'test.mp4'
            path.write_bytes(b'media')
            for streams in [[], [{'codec_type':'video'}], [{'codec_type':'audio'}]]:
                with patch('video_downloader.worker.subprocess.run') as run:
                    run.return_value.stdout = json.dumps({'streams': streams})
                    with self.assertRaises(RuntimeError):
                        verify_media(path)
            with patch('video_downloader.worker.subprocess.run') as run:
                run.return_value.stdout = json.dumps({'streams':[{'codec_type':'video'},{'codec_type':'audio'}]})
                verify_media(path)

    def test_publish_preserves_completed_file(self):
        with tempfile.TemporaryDirectory(prefix='video 空 ') as directory:
            root = Path(directory)
            stage = root/'stage'
            stage.mkdir()
            source = stage/'movie.mp4'
            source.write_bytes(b'new')
            (root/'movie.mp4').write_bytes(b'old')
            result = publish(source, root)
            self.assertEqual((root/'movie.mp4').read_bytes(), b'old')
            self.assertEqual(result.read_bytes(), b'new')
            self.assertNotEqual(result.name, 'movie.mp4')
