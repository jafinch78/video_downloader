"""Offline runtime checks for the distributed executable."""
import json
import platform
import struct
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path
from .runtime import media_tool, subprocess_options


def write_diagnostic(output: Path):
    data = {'python':platform.python_version(), 'platform':platform.platform(),
            'bits':struct.calcsize('P')*8, 'frozen':bool(getattr(sys,'frozen',False)),
            'yt_dlp':version('yt-dlp')}
    for tool in ('ffmpeg','ffprobe'):
        result=subprocess.run([media_tool(tool),'-version'],check=True,capture_output=True,
                              text=True,encoding='utf-8',errors='replace',timeout=30,**subprocess_options())
        data[tool]=result.stdout.splitlines()[0]
    output.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
