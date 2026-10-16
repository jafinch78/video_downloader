"""Package an existing Windows build; does not imply native release validation."""
import argparse
import hashlib
import zipfile
from pathlib import Path


def package_release(app: Path, output: Path) -> Path:
    executable = app/'VideoDownloader.exe'
    if not executable.is_file():
        raise ValueError('Build the Windows executable before packaging.')
    with executable.open('rb') as stream:
        if stream.read(2) != b'MZ':
            raise ValueError('Build output is not a Windows executable.')
    output.mkdir(parents=True, exist_ok=True)
    archive = output/'VideoDownloader-0.1.0-Windows-x64.zip'
    if archive.exists():
        raise FileExistsError(f'Refusing to overwrite {archive}')
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for path in sorted(app.rglob('*')):
            if path.is_file():
                z.write(path, str(Path(app.name)/path.relative_to(app)))
    with archive.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    archive.with_suffix('.zip.sha256').write_text(f'{digest}  {archive.name}\n', encoding='utf-8')
    return archive


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--app', type=Path, default=Path('dist/VideoDownloader'))
    parser.add_argument('--output', type=Path, default=Path('dist/releases'))
    args = parser.parse_args()
    print(package_release(args.app, args.output))
