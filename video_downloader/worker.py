"""Isolated downloader with private JSON event transport and verified output."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from .runtime import media_tool, subprocess_options
from .validation import validate_url, validate_destination


class UserError(RuntimeError):
    """An application-authored message safe for the status area."""


def safe_error(exc: Exception) -> str:
    if isinstance(exc, UserError):
        return str(exc)
    text = str(exc).lower()
    if isinstance(exc, PermissionError):
        return 'Permission denied. Choose a writable folder and close files that are in use.'
    if isinstance(exc, OSError) and exc.errno == 28:
        return 'The destination disk is full. Free space and retry.'
    if 'format' in text and ('not available' in text or 'requested' in text):
        return 'No supported video-with-audio format is available for this URL.'
    if any(word in text for word in ('javascript', 'js runtime', 'challenge')):
        return 'This site requires a JavaScript runtime or extractor capability outside this bundle.'
    if any(word in text for word in ('login', 'sign in', 'authentication', '401', '403', 'private video')):
        return 'The website denied access or requires authentication. Try a public video URL.'
    if any(word in text for word in ('connection', 'connect', 'timeout', 'download webpage', '404', 'resolve')):
        return 'Unable to reach the media. Check your internet connection, website access, and URL.'
    if isinstance(exc, subprocess.SubprocessError):
        return 'The media tool failed. Check free disk space and restore the complete portable application folder.'
    return 'Unable to download this video. Check the URL and destination; this site may require a newer extractor or unsupported capabilities.'


@contextmanager
def download_lock(stage: Path):
    # OS locks are released even when a worker crashes or is forcibly cancelled.
    # Keep the lock inode: unlinking it would let concurrent workers lock different files.
    with (stage/'.download.lock').open('a+b') as stream:
        stream.seek(0, 2)
        if stream.tell() == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise UserError('This URL is already being downloaded to this folder by another application instance.') from None
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def progress_event(data: dict) -> dict:
    total = data.get('total_bytes') or data.get('total_bytes_estimate')
    percent = min(100, max(0, data.get('downloaded_bytes', 0) * 100 / total)) if total else None
    return {'type': 'progress', 'percent': percent}


class Logger:
    def __init__(self, emit):
        self.emit = emit

    def debug(self, message):
        pass

    def warning(self, message):
        self.emit({'type': 'status', 'message': 'Extractor warning: ' + safe_error(Exception(message))})

    def error(self, message):
        pass  # the caught exception becomes one terminal error


def download_options(stage: Path, emit) -> dict:
    return {
        'noplaylist': True,
        'extract_flat': 'in_playlist',
        'lazy_playlist': True,
        'playlistend': 1,
        'format': 'bv[vcodec^=avc1][ext=mp4]+ba[acodec^=mp4a]/b[ext=mp4][vcodec!=?none][acodec!=?none]/bv+ba/b[vcodec!=?none][acodec!=?none]',
        'merge_output_format': 'mp4/mkv',
        'outtmpl': str(stage / '%(title).100B [%(id).60B].%(ext)s'),
        'windowsfilenames': True,
        'nooverwrites': True,
        'continuedl': True,
        'ffmpeg_location': media_tool('ffmpeg'),
        'logger': Logger(emit),
        'progress_hooks': [lambda data: emit(progress_event(data))],
        'postprocessor_hooks': [lambda data: emit({'type': 'status', 'message': 'Combining video and audio…'})],
        'socket_timeout': 30,
        'retries': 3,
        'quiet': True,
        'noprogress': True,
        'cachedir': False,
        'color': {'stderr': 'never', 'stdout': 'never'},
    }


def verify_media(path: Path) -> None:
    if not path.is_file() or not path.stat().st_size:
        raise UserError('The completed media file is missing or empty.')
    result = subprocess.run([media_tool('ffprobe'), '-v', 'error', '-show_streams', '-of', 'json', str(path)],
                            check=True, capture_output=True, text=True, encoding='utf-8', timeout=60,
                            **subprocess_options())
    types = {s.get('codec_type') for s in json.loads(result.stdout).get('streams', [])
             if not s.get('disposition', {}).get('attached_pic')}
    if not {'video', 'audio'} <= types:
        raise UserError('This media does not contain both video and audio. No completed file was saved.')


def publish(source: Path, destination: Path) -> Path:
    # Same-filesystem move/link: never expose an unfinished file or overwrite one.
    for index in range(10000):
        suffix = '' if index == 0 else f' ({index})'
        target = destination / f'{source.stem}{suffix}{source.suffix}'
        try:
            if os.name == 'nt':
                os.rename(source, target)  # Windows rename fails if target exists
            else:
                os.link(source, target)
                source.unlink()
            return target
        except FileExistsError:
            continue
    raise UserError('Too many files with this name. Select another destination.')


def run_download(url: str, destination: Path, emit) -> Path:
    url = validate_url(url)
    destination = validate_destination(str(destination))
    media_tool('ffprobe')
    # Stable URL hash permits partial resumption without storing the URL itself.
    stage = destination / '.video-downloader-partials' / hashlib.sha256(url.encode()).hexdigest()[:24]
    stage.mkdir(parents=True, exist_ok=True)
    with download_lock(stage):
        return _download_in_stage(url, destination, stage, emit)


def _download_in_stage(url, destination, stage, emit):
    from yt_dlp import YoutubeDL
    emit({'type': 'status', 'message': 'Reading video information…'})
    with YoutubeDL(download_options(stage, emit)) as downloader:
        info = downloader.extract_info(url, download=False)
        if not info or info.get('_type') in ('playlist', 'multi_video') or 'entries' in info:
            raise UserError('Enter a URL for one video, rather than a playlist.')
        info = downloader.process_ie_result(info, download=True)
        candidate = info.get('filepath') or info.get('_filename') or downloader.prepare_filename(info)
        source = Path(candidate).resolve()
        # Postprocessing can change the extension.
        if not source.is_file():
            stem = Path(downloader.prepare_filename(info)).stem
            candidates = [p for p in stage.iterdir() if p.stem == stem and p.suffix in ('.mp4', '.mkv', '.webm', '.mov', '.flv')]
            if len(candidates) != 1:
                raise UserError('Unable to locate the merged media file.')
            source = candidates[0].resolve()
        if source.parent != stage.resolve():
            raise UserError('Extractor returned an unexpected output location.')
        emit({'type': 'status', 'message': 'Checking video and audio…'})
        verify_media(source)
        final = publish(source, destination)
    try:
        stage.rmdir()
        stage.parent.rmdir()
    except OSError:
        pass
    emit({'type': 'complete', 'path': str(final)})
    return final


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--destination', required=True)
    args = parser.parse_args(argv)
    event_path = os.environ.get('VIDEO_DOWNLOADER_EVENTS')
    stream = open(event_path, 'a', encoding='utf-8', buffering=1) if event_path else sys.stdout
    def emit(event):
        if stream is None:
            raise UserError('Worker requires an event transport.')
        print(json.dumps(event, ensure_ascii=True), file=stream, flush=True)
    try:
        try:
            url = validate_url(args.url)
            destination = validate_destination(args.destination)
        except ValueError as exc:
            raise UserError(str(exc)) from None
        run_download(url, destination, emit)
        return 0
    except Exception as exc:
        message = safe_error(exc)
        emit({'type': 'error', 'message': message + '\nPartial downloads are retained for retry.'})
        return 1
    finally:
        if event_path:
            stream.close()


if __name__ == '__main__':
    sys.exit(main())
