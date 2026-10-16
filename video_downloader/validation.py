"""Validate local inputs and remove sensitive URL components from diagnostics."""
import re
import tempfile
from pathlib import Path
from urllib.parse import urlsplit


def validate_url(value: str) -> str:
    value = value.strip()
    try:
        parsed = urlsplit(value)
        port = parsed.port
        if (parsed.scheme not in ('http', 'https') or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or any(c.isspace() or ord(c) < 32 for c in value)):
            raise ValueError()
    except ValueError:
        raise ValueError('Enter a valid HTTP or HTTPS URL without embedded credentials.') from None
    return value


def validate_destination(value: str) -> Path:
    if not value.strip():
        raise ValueError('Select a destination folder.')
    path = Path(value).expanduser().resolve()
    try:
        if not path.is_dir():
            raise OSError()
        with tempfile.TemporaryFile(dir=path):
            pass
    except OSError:
        raise ValueError('Select an existing writable destination folder.') from None
    return path


def redact_diagnostic(text: str) -> str:
    def clean(match):
        try:
            parsed = urlsplit(match.group())
            return f'{parsed.scheme}://{parsed.hostname or "[host]"}/[URL redacted]'
        except ValueError:
            return '[URL redacted]'
    return re.sub(r'https?://[^\s<>"\']+', clean, str(text), flags=re.IGNORECASE)
