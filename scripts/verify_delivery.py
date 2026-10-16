"""Reject source-only or incomplete archives when a Windows application is expected."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from scripts.build_support import validate_assets

REQUIRED = (
    'VideoDownloader.exe',
    '_internal/python312.dll',
    '_internal/vcruntime140.dll',
    '_internal/certifi/cacert.pem',
    '_internal/_tcl_data/init.tcl',
    '_internal/_tk_data/tk.tcl',
    '_internal/assets/ffmpeg.exe',
    '_internal/assets/ffprobe.exe',
    '_internal/assets/manifest.json',
    '_internal/assets/FFmpeg-LICENSE.txt',
    '_internal/assets/ffmpeg-source.zip',
    'README.txt',
    'THIRD_PARTY_NOTICES.md',
)



def bundle_inventory(root: Path) -> dict[str,str]:
    inventory={}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError(f'Bundle contains a symlink rather than a retained file: {path.name}')
        if path.is_file() and path.relative_to(root)!=Path('bundle-validation.json'):
            with path.open('rb') as stream:
                inventory[path.relative_to(root).as_posix()]=hashlib.file_digest(stream,'sha256').hexdigest()
    return inventory

def verify_folder(root: Path):
    for relative in REQUIRED:
        path=root/relative
        if not path.is_file() or not path.stat().st_size:
            raise ValueError(f'Application delivery is incomplete: missing {relative}')
    for relative in ('VideoDownloader.exe','_internal/python312.dll'):
        with (root/relative).open('rb') as stream:
            if stream.read(2)!=b'MZ':
                raise ValueError(f'Not a Windows binary: {relative}')
    if not any(p.is_file() for p in (root/'third-party-licenses').rglob('*')):
        raise ValueError('Application delivery is incomplete: missing third-party license files')
    validate_assets(root/'_internal/assets')


def verify_zip(path: Path):
    prefix='VideoDownloader/'
    with zipfile.ZipFile(path) as archive:
        names=set(archive.namelist())
        for relative in REQUIRED:
            name=prefix+relative
            if name not in names or archive.getinfo(name).file_size==0:
                raise ValueError(f'Application ZIP is incomplete: missing {relative}')
        for relative in ('VideoDownloader.exe','_internal/python312.dll','_internal/assets/ffmpeg.exe','_internal/assets/ffprobe.exe'):
            with archive.open(prefix+relative) as stream:
                if stream.read(2)!=b'MZ':
                    raise ValueError(f'Not a Windows binary: {relative}')
        if not any(n.startswith(prefix+'third-party-licenses/') and not n.endswith('/') for n in names):
            raise ValueError('Application ZIP is missing third-party licenses')
        manifest=json.loads(archive.read(prefix+'_internal/assets/manifest.json'))
        for name in ('ffmpeg.exe','ffprobe.exe','FFmpeg-LICENSE.txt','ffmpeg-source.zip'):
            with archive.open(prefix+'_internal/assets/'+name) as stream:
                actual=hashlib.file_digest(stream,'sha256').hexdigest()
            if manifest.get('files',{}).get(name)!=actual:
                raise ValueError(f'Bundled media asset hash mismatch: {name}')
        if prefix+'bundle-validation.json' not in names:
            raise ValueError('Application ZIP is missing the exact-bundle smoke report')
        report=json.loads(archive.read(prefix+'bundle-validation.json'))
        actual_files={}
        for name in names:
            if name.endswith('/') or name==prefix+'bundle-validation.json':
                continue
            if not name.startswith(prefix):
                raise ValueError('Unexpected file outside the application folder')
            with archive.open(name) as stream:
                actual_files[name[len(prefix):]]=hashlib.file_digest(stream,'sha256').hexdigest()
        if not report.get('automated_pass') or report.get('bundle_files')!=actual_files:
            raise ValueError('Application ZIP differs from the successfully tested bundle')
        corrupt=archive.testzip()
        if corrupt:
            raise ValueError(f'Archive CRC failure: {corrupt}')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--folder',type=Path)
    group.add_argument('--zip',type=Path)
    args=parser.parse_args()
    verify_folder(args.folder) if args.folder else verify_zip(args.zip)
    print('Artifact structure and media asset integrity PASS. Runtime execution/native OS checks are separate.')
