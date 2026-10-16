"""Offline runtime checks for the distributed executable."""
import importlib
import json
import ssl
import platform
import struct
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path
from .runtime import media_tool, subprocess_options
from .dependencies import PACKAGES


def check_dependencies() -> dict:
    packages=[]
    for distribution, expected, module_name in PACKAGES:
        actual=version(distribution)
        if actual != expected:
            raise RuntimeError(f'{distribution}: expected {expected}, found {actual}')
        module=importlib.import_module(module_name)
        if getattr(sys,'frozen',False):
            location=Path(module.__file__).resolve()
            if not location.is_relative_to(Path(sys._MEIPASS).resolve()):
                raise RuntimeError(f'{distribution} was loaded outside the portable package')
        packages.append({'name':distribution,'version':actual,'module':module_name,'loaded_from':str(Path(module.__file__).resolve()),'passed':True})
    import brotli
    import certifi
    from Cryptodome.Cipher import AES
    payload=b'video-downloader-native-dependency-check'
    if brotli.decompress(brotli.compress(payload)) != payload:
        raise RuntimeError('Native Brotli round trip failed')
    cipher=AES.new(bytes(16),AES.MODE_ECB)
    if len(cipher.encrypt(bytes(16))) != 16:
        raise RuntimeError('Native AES check failed')
    context=ssl.create_default_context(cafile=certifi.where())
    if not context.get_ca_certs():
        raise RuntimeError('Bundled TLS certificate store is empty')
    return {'packages':packages,'native_brotli':True,'native_crypto':True,'tls_certificates':True}


def write_diagnostic(output: Path, check_gui=False):
    data={'python':platform.python_version(), 'platform':platform.platform(),
          'bits':struct.calcsize('P')*8, 'frozen':bool(getattr(sys,'frozen',False)), 'passed':False}
    output.parent.mkdir(parents=True,exist_ok=True)
    try:
        data['dependencies']=check_dependencies()
        data['yt_dlp']=version('yt-dlp')
        for tool in ('ffmpeg','ffprobe'):
            result=subprocess.run([media_tool(tool),'-version'],check=True,capture_output=True,
                                  text=True,encoding='utf-8',errors='replace',timeout=30,**subprocess_options())
            data[tool]=result.stdout.splitlines()[0]
        if check_gui:
            import gc
            import tkinter as tk
            root=tk.Tk()
            try:
                root.withdraw()
                root.update()
                data['tkinter']={'passed':True, 'tcl':root.tk.call('info','patchlevel'), 'tk':root.tk.call('package','require','Tk')}
            finally:
                root.destroy()
                del root
                gc.collect()
        data['passed']=True
    except Exception as exc:
        data['error']=str(exc)
        raise
    finally:
        output.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
