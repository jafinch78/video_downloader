"""Release prerequisites shared by the build and native checklist."""
import hashlib
import json
import platform
import os
import shutil
import ssl
import tarfile
import tempfile
import urllib.request
import urllib.parse
import zipfile
import struct
import sys
from pathlib import Path, PurePosixPath


# Version-specific checksums independently published by Microsoft's package repositories.
FFMPEG_URL = 'https://github.com/GyanD/codexffmpeg/releases/download/6.1.1/ffmpeg-6.1.1-essentials_build.zip'
FFMPEG_SHA256 = '742e32fc9f92681f9f254b925e1b613fdd8074ba40749d4879aefdb009b94cc5'
FFMPEG_CHECKSUM_REFERENCE = 'https://raw.githubusercontent.com/microsoft/winget-pkgs/master/manifests/g/Gyan/FFmpeg/Essentials/6.1.1/Gyan.FFmpeg.Essentials.installer.yaml'
SOURCE_URL = 'https://github.com/ffmpeg/ffmpeg/archive/n6.1.1.tar.gz'
SOURCE_SHA512 = 'a84209fe36a2a0262ebc34b727e7600b12d4739991a95599d7b4df533791b12e2e43586ccc6ff26aab2f935a3049866204e322ec0c5e49e378fc175ded34e183'
SOURCE_CHECKSUM_REFERENCE = 'https://raw.githubusercontent.com/microsoft/vcpkg/2024.02.14/ports/ffmpeg/portfile.cmake'


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def require_release_runtime(version=None, system=None, bits=None):
    version = tuple(version or sys.version_info[:3])
    system = system or platform.system()
    bits = bits or struct.calcsize('P') * 8
    if version != (3, 12, 7) or system != 'Windows' or bits != 64:
        raise ValueError('Build requires Windows and Python 3.12.7 x64, including Tcl/Tk.')


def validate_assets(root: Path) -> dict:
    try:
        manifest = json.loads((root/'manifest.json').read_text(encoding='utf-8'))
        required = {'ffmpeg.exe', 'ffprobe.exe', 'FFmpeg-LICENSE.txt', 'ffmpeg-source.zip'}
        if not required <= manifest['files'].keys():
            raise ValueError('Required media tools, license, or corresponding source are missing.')
        if not manifest['archive_url'].startswith('https://') or len(manifest['archive_sha256']) != 64:
            raise ValueError('Missing upstream archive provenance.')
        for name in required:
            path = root/name
            if not path.is_file() or path.stat().st_size == 0 or sha256(path) != manifest['files'][name]:
                raise ValueError(f'Asset is missing or its hash differs: {name}')
        for name in ('ffmpeg.exe', 'ffprobe.exe'):
            with (root/name).open('rb') as stream:
                if stream.read(2) != b'MZ':
                    raise ValueError(f'Not a Windows executable: {name}')
        return manifest
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError('Prepare verified FFmpeg assets first; see README.md.') from exc


def _download_verified(url: str, cache: Path, expected: str, algorithm: str) -> Path:
    if not url.startswith('https://'):
        raise ValueError('Dependency download requires HTTPS.')
    cache.mkdir(parents=True,exist_ok=True)
    name=Path(urllib.parse.urlsplit(url).path).name
    destination=cache/name
    def matches(path):
        with path.open('rb') as stream:
            return hashlib.file_digest(stream,algorithm).hexdigest()==expected
    if destination.is_file():
        if matches(destination):
            print(f'Using verified cached archive: {name}',flush=True)
            return destination
        print(f'Cached checksum mismatch; replacing damaged download: {name}',flush=True)
        destination.unlink()
    context=ssl.create_default_context()
    try:
        import certifi
        context=ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass  # Standard-library TLS verification remains enabled.
    print(f'Downloading {url}',flush=True)
    with tempfile.TemporaryDirectory(prefix='video-download-',dir=cache) as temporary:
        partial=Path(temporary)/name
        with urllib.request.urlopen(url,timeout=90,context=context) as response, partial.open('wb') as output:
            received=0
            next_update=8*1024*1024
            while True:
                block=response.read(1024*1024)
                if not block:
                    break
                output.write(block)
                received+=len(block)
                if received>=next_update:
                    print(f'  {name}: {received/(1024*1024):.0f} MiB received',flush=True)
                    next_update=received+8*1024*1024
        if not matches(partial):
            raise ValueError(f'Dependency checksum mismatch for {name}; download was not used.')
        print(f'Published {algorithm.upper()} checksum PASS: {name}',flush=True)
        os.replace(partial,destination)
    return destination


def ensure_assets(root: Path, cache: Path | None = None) -> dict:
    if (root/'manifest.json').is_file():
        manifest=validate_assets(root)
        print('Existing FFmpeg assets and manifest hashes PASS; no downloads needed.',flush=True)
        if manifest.get('source_scope'):
            print('Source archive scope: '+manifest['source_scope'],flush=True)
        return manifest
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise ValueError('Missing manifest in nonempty assets folder; refusing to overwrite existing files. Preserve or rename that folder before retrying.')
    print('FFmpeg assets are missing. Preparing checksum-verified FFmpeg 6.1.1 x64...',flush=True)
    cache=cache or Path(tempfile.gettempdir())/'VideoDownloader-build-cache'
    binary=_download_verified(FFMPEG_URL,cache,FFMPEG_SHA256,'sha256')
    source=_download_verified(SOURCE_URL,cache,SOURCE_SHA512,'sha512')
    root.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='video-assets-',dir=root.parent) as temporary:
        staged=Path(temporary)/'assets'
        staged.mkdir()
        with zipfile.ZipFile(binary) as archive:
            for wanted in ('ffmpeg.exe','ffprobe.exe'):
                matches=[n for n in archive.namelist() if PurePosixPath(n).name.lower()==wanted]
                if len(matches)!=1:
                    raise ValueError(f'Expected one {wanted} in the verified publisher archive.')
                with archive.open(matches[0]) as inp,(staged/wanted).open('wb') as output:
                    shutil.copyfileobj(inp,output)
            licenses=[n for n in archive.namelist() if PurePosixPath(n).name.lower() in ('license','license.txt')]
            if len(licenses)!=1:
                raise ValueError('Expected the publisher license in the verified FFmpeg archive.')
            with archive.open(licenses[0]) as inp,(staged/'FFmpeg-LICENSE.txt').open('wb') as output:
                shutil.copyfileobj(inp,output)
        provenance={'archive_url':FFMPEG_URL,'archive_sha256':FFMPEG_SHA256,
                    'checksum_reference':FFMPEG_CHECKSUM_REFERENCE,
                    'upstream_source_url':SOURCE_URL,'upstream_source_sha512':SOURCE_SHA512,
                    'source_checksum_reference':SOURCE_CHECKSUM_REFERENCE,
                    'source_scope':'Verified upstream FFmpeg source. Additional third-party vendor build/dependency sources are not assembled in this ZIP.',
                    'compatibility':'Windows 1607 execution remains to be tested by the local and frozen checks.'}
        print('Packing verified upstream FFmpeg source and provenance...',flush=True)
        with tarfile.open(source,'r:gz') as tar, zipfile.ZipFile(staged/'ffmpeg-source.zip','w',compression=zipfile.ZIP_DEFLATED) as output:
            count=0
            for member in tar:
                path=PurePosixPath(member.name)
                if path.is_absolute() or '..' in path.parts:
                    raise ValueError('Unsafe path in the source archive.')
                if member.isdir():
                    continue
                if not member.isfile():
                    raise ValueError('Unexpected non-file member in the source archive.')
                with tar.extractfile(member) as inp,output.open(path.as_posix(),'w') as out:
                    shutil.copyfileobj(inp,out)
                count+=1
            output.writestr('BOOTSTRAP-PROVENANCE.json',json.dumps(provenance,indent=2)+'\n')
            if not count:
                raise ValueError('The verified source archive contained no files.')
        provenance['files']={p.name:sha256(p) for p in staged.iterdir()}
        (staged/'manifest.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8')
        validate_assets(staged)
        if root.exists():
            root.rmdir()  # Only an empty preexisting folder may be removed.
        os.rename(staged,root)
    manifest=validate_assets(root)
    print(f'FFmpeg assets prepared and verified: {root.resolve()}',flush=True)
    print('Source archive scope: '+manifest['source_scope'],flush=True)
    print('Continue with the local native-library/GUI/media checks before building the EXE.',flush=True)
    return manifest


if __name__ == '__main__':
    require_release_runtime()
    ensure_assets(Path(__file__).resolve().parents[1]/'assets')
