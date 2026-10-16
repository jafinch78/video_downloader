import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from video_downloader.validation import validate_url, validate_destination, redact_diagnostic
from video_downloader.runtime import asset_path, worker_command

class ValidationTests(unittest.TestCase):
    def test_url(self):
        self.assertEqual(validate_url(' https://example.com/watch?v=123 '), 'https://example.com/watch?v=123')
        for value in ['', 'file:///tmp/a', 'https://', 'http://user:secret@example.com', 'https://host:bad', 'https://host/a\nb']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_url(value)

    def test_destination(self):
        with tempfile.TemporaryDirectory(prefix='video 空 ') as directory:
            self.assertEqual(validate_destination(directory), Path(directory).resolve())
            self.assertEqual(list(Path(directory).iterdir()), [])
            with self.assertRaises(ValueError):
                validate_destination(str(Path(directory) / 'absent'))

    def test_redaction(self):
        result = redact_diagnostic('Error https://user:password@example.com/watch?token=secret#private')
        for secret in ['user', 'password', 'secret', 'private']:
            self.assertNotIn(secret, result)
        self.assertIn('example.com', result)

    def test_runtime(self):
        with patch('sys.frozen', True, create=True), patch('sys._MEIPASS', '/tmp/bundle', create=True):
            self.assertEqual(asset_path('ffmpeg.exe'), Path('/tmp/bundle/assets/ffmpeg.exe'))
            command = worker_command('https://example.com', Path('/tmp/with space 空'))
            self.assertIn('--worker', command)
            self.assertEqual(command[-1], str(Path('/tmp/with space 空')))
        self.assertIn('video_downloader.worker', worker_command('https://example.com', Path('/tmp')))
