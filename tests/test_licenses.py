import tempfile
import unittest
from pathlib import Path
from scripts.collect_licenses import collect

class LicenseTests(unittest.TestCase):
    def test_collects_installed_dependency_notices(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            collect(root, include_runtime=False)
            self.assertTrue(list(root.glob('yt-dlp/**/*')))
            self.assertTrue(list(root.glob('certifi/**/*')))
