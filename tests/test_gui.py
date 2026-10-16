import gc
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch
from video_downloader.gui import App, default_destination

class FakeController:
    active=False
    def __init__(self):
        self.events=[]
        self.cancelled=False
    def start(self, url, destination):
        self.active=True
        self.url=url
        self.destination=destination
    def cancel(self):
        self.cancelled=True
    def poll(self):
        events,self.events=self.events,[]
        return events

class GuiTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root=tk.Tk()
        except tk.TclError as exc:
            self.skipTest(str(exc))
        self.root.withdraw()
        self.controller=FakeController()
        self.app=App(self.root, self.controller)
        self.temp=tempfile.TemporaryDirectory()
        self.app.destination.set(self.temp.name)
    def tearDown(self):
        if hasattr(self, 'app'):
            self.root.destroy()
            del self.app
            del self.root
            gc.collect()
            self.temp.cleanup()
    def test_download_and_completion(self):
        self.app.url.set('https://example.com/watch?v=1')
        self.app.start()
        self.assertTrue(self.app.download_button.instate(['disabled']))
        self.assertFalse(self.app.cancel_button.instate(['disabled']))
        self.controller.events=[{'type':'progress','percent':50}, {'type':'complete','path':str(Path(self.temp.name)/'video.mp4')}]
        self.controller.active=False
        self.app.tick()
        self.assertFalse(self.app.download_button.instate(['disabled']))
        self.assertIn('video.mp4', self.app.status.get('1.0','end'))
    def test_invalid_url_does_not_start(self):
        self.app.url.set('not a url')
        self.app.start()
        self.assertFalse(self.controller.active)
        self.assertIn('HTTP', self.app.status.get('1.0','end'))
    def test_error_restores_buttons(self):
        self.controller.events=[{'type':'error','message':'Download failed'}]
        self.app.tick()
        self.assertFalse(self.app.download_button.instate(['disabled']))
        self.assertIn('failed', self.app.status.get('1.0','end'))
    def test_close_cancel_confirmation(self):
        self.controller.active=True
        with patch('video_downloader.gui.messagebox.askyesno', return_value=False):
            self.app.close()
        self.assertFalse(self.controller.cancelled)
        with patch('video_downloader.gui.messagebox.askyesno', return_value=True):
            self.app.close()
        self.assertTrue(self.controller.cancelled)

class DefaultDestinationTests(unittest.TestCase):
    def test_home_fallback_and_downloads(self):
        with tempfile.TemporaryDirectory() as directory, patch('pathlib.Path.home', return_value=Path(directory)):
            self.assertEqual(default_destination(), Path(directory))
            downloads=Path(directory)/'Downloads'
            downloads.mkdir()
            self.assertEqual(default_destination(), downloads)
