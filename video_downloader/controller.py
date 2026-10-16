"""Supervise one download process without blocking the GUI thread."""
import json
import os
import queue
import signal
import subprocess
import threading
from pathlib import Path
from .runtime import worker_command, subprocess_options
from .validation import redact_diagnostic


class DownloadController:
    def __init__(self):
        self._events = queue.Queue()
        self._process = None
        self._active = False
        self._cancelled = threading.Event()
        self._lock = threading.Lock()

    @property
    def active(self) -> bool:
        return self._active

    def start(self, url: str, destination: Path) -> None:
        with self._lock:
            if self.active:
                raise RuntimeError('A download is already running.')
            self._cancelled.clear()
            options = subprocess_options()
            if os.name != 'nt':
                options['start_new_session'] = True
            self._process = subprocess.Popen(worker_command(url, destination), stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, encoding='utf-8', errors='replace', **options)
            self._active = True
            threading.Thread(target=self._monitor, args=(self._process,), daemon=True).start()

    def _monitor(self, process):
        complete = None
        error = None
        try:
            with process.stdout:
                for line in process.stdout:
                    try:
                        event = json.loads(line)
                        if not isinstance(event, dict):
                            continue
                        kind = event.get('type')
                        if kind == 'complete' and isinstance(event.get('path'), str):
                            complete = event
                        elif kind == 'error':
                            error = {'type': 'error', 'message': redact_diagnostic(event.get('message', 'Download failed.'))}
                        elif kind in ('status', 'progress'):
                            if kind == 'status':
                                event['message'] = redact_diagnostic(event.get('message', ''))
                            self._events.put(event)
                    except (ValueError, TypeError):
                        continue
            code = process.wait()
            if self._cancelled.is_set():
                terminal = {'type': 'cancelled', 'message': 'Cancelled. Partial downloads are retained for retry.'}
            elif code == 0 and complete and not error:
                terminal = complete
            else:
                terminal = error or {'type': 'error', 'message': 'The download worker stopped without a verified output. Partial downloads are retained for retry.'}
        except Exception:
            terminal = {'type': 'error', 'message': 'Unable to read the download worker result.'}
        with self._lock:
            self._events.put(terminal)
            self._active = False

    def cancel(self) -> None:
        with self._lock:
            if not self.active or self._cancelled.is_set():
                return
            self._cancelled.set()
            process = self._process
        threading.Thread(target=self._terminate_tree, args=(process,), daemon=True).start()

    @staticmethod
    def _terminate_tree(process):
        try:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                               capture_output=True, timeout=15, **subprocess_options())
            else:
                os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, OSError, subprocess.TimeoutExpired):
            if process.poll() is None:
                process.kill()

    def poll(self) -> list[dict]:
        result = []
        while True:
            try:
                result.append(self._events.get_nowait())
            except queue.Empty:
                return result
