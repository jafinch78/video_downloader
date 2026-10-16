"""Import a publisher-checksummed static Windows FFmpeg build and its sources."""
import argparse
import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from scripts.build_support import sha256, validate_assets


def prepare(archive: Path, expected: str, url: str, source: Path, source_sha: str, destination: Path):
    if not url.startswith('https://'):
        raise ValueError('Record the authoritative HTTPS binary archive URL.')
    if sha256(archive) != expected.lower() or sha256(source) != source_sha.lower():
        raise ValueError('Archive checksum mismatch; no assets were imported.')
    if destination.exists():
        raise FileExistsError('Asset folder exists. Preserve it or move it explicitly before preparing another version.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
        target = Path(temporary)/'assets'
        target.mkdir()
        with zipfile.ZipFile(archive) as z:
            for name in ('ffmpeg.exe', 'ffprobe.exe', 'LICENSE.txt'):
                matches = [n for n in z.namelist() if Path(n).name.lower() == name.lower()]
                if len(matches) != 1:
                    raise ValueError(f'Expected one {name} in the static Windows archive.')
                output = 'FFmpeg-LICENSE.txt' if name == 'LICENSE.txt' else name
                with z.open(matches[0]) as inp, (target/output).open('wb') as out:
                    shutil.copyfileobj(inp, out)
        if not zipfile.is_zipfile(source):
            raise ValueError('Supply corresponding source, build scripts, and required dependency sources as a ZIP.')
        shutil.copy2(source, target/'ffmpeg-source.zip')
        files = {p.name:sha256(p) for p in target.iterdir()}
        manifest = {'archive_url':url, 'archive_sha256':expected.lower(), 'source_sha256':source_sha.lower(), 'files':files,
                    'compatibility':'Windows 10 1607 unverified until native release checklist passes'}
        (target/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
        validate_assets(target)
        shutil.move(str(target), destination)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',required=True,type=Path)
    parser.add_argument('--sha256',required=True)
    parser.add_argument('--source-url',required=True)
    parser.add_argument('--source-archive',required=True,type=Path)
    parser.add_argument('--source-sha256',required=True)
    parser.add_argument('--destination',default=Path('assets'),type=Path)
    args=parser.parse_args()
    prepare(args.archive,args.sha256,args.source_url,args.source_archive,args.source_sha256,args.destination)
    print('Verified assets imported. Native Windows 1607 testing is still required.')
