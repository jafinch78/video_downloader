"""Tk GUI; all widget access stays on the main thread."""
import math
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from pathlib import Path
from .controller import DownloadController
from .validation import validate_url, validate_destination, redact_diagnostic


def default_destination() -> Path:
    downloads = Path.home() / 'Downloads'
    return downloads if downloads.is_dir() else Path.home()


class App:
    def __init__(self, root, controller=None):
        self.root = root
        self.controller = controller or DownloadController()
        self.closing = False
        self.root.title('Video Downloader')
        self.root.geometry('720x460')
        self.root.minsize(560, 380)
        self.url = tk.StringVar()
        self.destination = tk.StringVar(value=str(default_destination()))
        frame = ttk.Frame(root, padding=18)
        frame.pack(fill='both', expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(8, weight=1)
        ttk.Label(frame, text='Video Downloader', font=('Segoe UI', 17, 'bold')).grid(row=0, column=0, sticky='w')
        ttk.Label(frame, text='Paste a video URL and choose where to save video with audio.').grid(row=1, column=0, columnspan=2, sticky='w', pady=(3, 16))
        ttk.Label(frame, text='Video URL').grid(row=2, column=0, sticky='w')
        self.url_entry = ttk.Entry(frame, textvariable=self.url)
        self.url_entry.grid(row=3, column=0, columnspan=2, sticky='ew', pady=(4, 12))
        ttk.Label(frame, text='Save to folder').grid(row=4, column=0, sticky='w')
        self.destination_entry = ttk.Entry(frame, textvariable=self.destination)
        self.destination_entry.grid(row=5, column=0, sticky='ew', pady=(4, 12))
        self.browse_button = ttk.Button(frame, text='Browse…', command=self.browse)
        self.browse_button.grid(row=5, column=1, padx=(8, 0), pady=(4, 12))
        buttons = ttk.Frame(frame)
        buttons.grid(row=6, column=0, columnspan=2, sticky='w')
        self.download_button = ttk.Button(buttons, text='Download', command=self.start)
        self.download_button.pack(side='left')
        self.cancel_button = ttk.Button(buttons, text='Cancel', command=self.cancel, state='disabled')
        self.cancel_button.pack(side='left', padx=8)
        self.progress = ttk.Progressbar(frame, maximum=100)
        self.progress.grid(row=7, column=0, columnspan=2, sticky='ew', pady=12)
        self.status = ScrolledText(frame, height=7, wrap='word', state='disabled')
        self.status.grid(row=8, column=0, columnspan=2, sticky='nsew')
        self.log('Ready. Downloads need internet access. One video per download.')
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.url_entry.focus_set()
        self.timer = self.root.after(100, self.tick)

    def log(self, message):
        self.status.configure(state='normal')
        self.status.insert('end', redact_diagnostic(str(message)) + '\n')
        # Bound retained log text during long operations.
        if int(self.status.index('end-1c').split('.')[0]) > 500:
            self.status.delete('1.0', '101.0')
        self.status.see('end')
        self.status.configure(state='disabled')

    def browse(self):
        path = filedialog.askdirectory(parent=self.root, initialdir=self.destination.get(), mustexist=True)
        if path:
            self.destination.set(path)

    def set_busy(self, busy):
        for widget in (self.download_button, self.url_entry, self.destination_entry, self.browse_button):
            widget.state(['disabled'] if busy else ['!disabled'])
        self.cancel_button.state(['!disabled'] if busy else ['disabled'])

    def start(self):
        try:
            url = validate_url(self.url.get())
            destination = validate_destination(self.destination.get())
            self.controller.start(url, destination)
        except (ValueError, OSError, RuntimeError) as exc:
            self.log(str(exc))
            return
        self.progress.stop()
        self.progress.configure(mode='indeterminate', value=0)
        self.progress.start(12)
        self.set_busy(True)
        self.log('Starting download…')

    def cancel(self):
        self.cancel_button.state(['disabled'])
        self.controller.cancel()
        self.log('Cancelling…')

    def tick(self):
        self.root.after_cancel(self.timer)
        for event in self.controller.poll():
            kind = event.get('type')
            if kind == 'progress':
                percent = event.get('percent')
                if isinstance(percent, (float, int)) and math.isfinite(percent):
                    self.progress.stop()
                    self.progress.configure(mode='determinate', value=max(0, min(100, percent)))
            elif kind == 'complete':
                self.progress.stop()
                self.progress.configure(mode='determinate', value=100)
                self.log('Saved video with audio:\n' + event['path'])
            elif kind in ('status', 'error', 'cancelled'):
                self.log(event.get('message', ''))
        if not self.controller.active:
            self.progress.stop()
            self.set_busy(False)
            if self.closing:
                self.root.destroy()
                return
        self.timer = self.root.after(100, self.tick)

    def close(self):
        if self.controller.active:
            if not messagebox.askyesno('Download in progress', 'Cancel the download and exit?', parent=self.root):
                return
            self.closing = True
            self.cancel()
        else:
            self.root.destroy()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()
