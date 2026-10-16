import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from scripts.collect_licenses import collect

class LicenseTests(unittest.TestCase):
    def test_collects_installed_dependency_notices(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            collect(root, include_runtime=False)
            self.assertTrue(list(root.glob('yt-dlp/**/*')))
            self.assertTrue(list(root.glob('certifi/**/*')))

    def test_windows_install_without_separate_tcl_tk_notices(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory)/'python'
            base.mkdir()
            (base/'LICENSE.txt').write_text('Python license fixture')
            output=Path(directory)/'notices'
            with patch('scripts.collect_licenses.sys.base_prefix', str(base)):
                collect(output)
            for name in ('Tcl', 'Tk'):
                text=(output/name/'LICENSE.txt').read_text()
                self.assertIn('permission', text.lower())
                self.assertGreater(len(text), 2000)
            self.assertEqual((output/'Python/LICENSE.txt').read_text(), 'Python license fixture')

    def test_rejects_altered_fallback_notice(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory)/'python'
            base.mkdir()
            (base/'LICENSE.txt').write_text('Python fixture')
            original=Path.read_bytes
            def altered(path):
                if path.name=='Tcl-8.6.13.txt':
                    return b'altered notice'
                return original(path)
            with patch('scripts.collect_licenses.sys.base_prefix', str(base)), patch.object(Path, 'read_bytes', altered):
                with self.assertRaisesRegex(ValueError, 'altered bundled Tcl'):
                    collect(Path(directory)/'notices')
