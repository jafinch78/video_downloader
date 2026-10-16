"""Isolated downloader. stdout carries JSON events, never extractor console output."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from .runtime import media_tool, subprocess_options
from .validation import validate_url, validate_destination, redact_diagnostic


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
        self.emit({'type': 'status', 'message': redact_diagnostic(message)})

    def error(self, message):
        pass  # the caught exception becomes one terminal error


def download_options(stage: Path, emit) -> dict:
    return {
        'noplaylist': True,
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
        raise RuntimeError('The completed media file is missing or empty.')
    result = subprocess.run([media_tool('ffprobe'), '-v', 'error', '-show_streams', '-of', 'json', str(path)],
                            check=True, capture_output=True, text=True, encoding='utf-8', timeout=60,
                            **subprocess_options())
    types = {s.get('codec_type') for s in json.loads(result.stdout).get('streams', [])
             if not s.get('disposition', {}).get('attached_pic')}
    if not {'video', 'audio'} <= types:
        raise RuntimeError('This media does not contain both video and audio. No completed file was saved.')


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
    raise RuntimeError('Too many files with this name. Select another destination.')


def run_download(url: str, destination: Path, emit) -> Path:
    from yt_dlp import YoutubeDL
    url = validate_url(url)
    destination = validate_destination(str(destination))
    media_tool('ffprobe')
    # Stable URL hash permits partial resumption without storing the URL itself.
    stage = destination / '.video-downloader-partials' / hashlib.sha256(url.encode()).hexdigest()[:24]
    stage.mkdir(parents=True, exist_ok=True)
    emit({'type': 'status', 'message': 'Reading video information…'})
    with YoutubeDL(download_options(stage, emit)) as downloader:
        info = downloader.extract_info(url, download=True)
        if not info or info.get('_type') in ('playlist', 'multi_video'):
            raise RuntimeError('Enter a URL for one video, rather than a playlist.')
        candidate = info.get('filepath') or info.get('_filename') or downloader.prepare_filename(info)
        source = Path(candidate).resolve()
        # Postprocessing can change the extension.
        if not source.is_file():
            stem = Path(downloader.prepare_filename(info)).stem
            candidates = [p for p in stage.iterdir() if p.stem == stem and p.suffix in ('.mp4', '.mkv', '.webm', '.mov', '.flv')]
            if len(candidates) != 1:
                raise RuntimeError('Unable to locate the merged media file.')
            source = candidates[0].resolve()
        if source.parent != stage.resolve():
            raise RuntimeError('Extractor returned an unexpected output location.')
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
            raise RuntimeError('Worker requires an event transport.')
        print(json.dumps(event, ensure_ascii=True), file=stream, flush=True)
    try:
        run_download(args.url, Path(args.destination), emit)
        return 0
    except Exception as exc:
        message = redact_diagnostic(str(exc)).replace('\x1b', '')
        emit({'type': 'error', 'message': message + '\nPartial downloads are retained for retry.'})
        return 1
    finally:
        if event_path:
            stream.close()


if __name__ == '__main__':
    sys.exit(main())
