"""Package an existing Windows build; does not imply native release validation."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from scripts.verify_delivery import verify_folder, verify_zip, bundle_inventory
from video_downloader.dependencies import PACKAGES


def package_release(app: Path, output: Path, smoke_report: Path = Path('logs/bundled-dependencies.json')) -> Path:
    executable = app/'VideoDownloader.exe'
    if not executable.is_file():
        raise ValueError('Build the Windows executable before packaging.')
    with executable.open('rb') as stream:
        if stream.read(2) != b'MZ':
            raise ValueError('Build output is not a Windows executable.')
    verify_folder(app)
    try:
        report=json.loads(smoke_report.read_text(encoding='utf-8'))
        runtime=report.get('runtime',{})
        imports={item['name']:item['version'] for item in runtime.get('dependencies',{}).get('packages',[]) if item.get('passed')}
        expected={name:pin for name,pin,module in PACKAGES}
        if report.get('bundle_files')!=bundle_inventory(app):
            raise ValueError('The runtime bundle differs from the dependency/media smoke test. Re-run the test.')
        if (not report.get('automated_pass') or report.get('exe_sha256')!=hashlib.sha256(executable.read_bytes()).hexdigest()
                or not runtime.get('frozen') or not runtime.get('passed') or runtime.get('python')!='3.12.7' or runtime.get('bits')!=64
                or not runtime.get('tkinter',{}).get('passed') or imports!=expected):
            raise ValueError('Smoke report does not prove this exact EXE and all pinned dependencies passed.')
    except (OSError,KeyError,TypeError,json.JSONDecodeError) as exc:
        raise ValueError('A passing bundled EXE dependency/media report is required before packaging.') from exc
    output.mkdir(parents=True, exist_ok=True)
    archive = output/'VideoDownloader-0.1.0-Windows-x64.zip'
    if archive.exists():
        raise FileExistsError(f'Refusing to overwrite {archive}')
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for path in sorted(app.rglob('*')):
            if path.is_file() and path.relative_to(app)!=Path('bundle-validation.json'):
                z.write(path, str(Path(app.name)/path.relative_to(app)))
        z.write(smoke_report,str(Path(app.name)/'bundle-validation.json'))
    try:
        verify_zip(archive)
    except Exception:
        archive.unlink()
        raise
    with archive.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    archive.with_suffix('.zip.sha256').write_text(f'{digest}  {archive.name}\n', encoding='utf-8')
    return archive


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--app', type=Path, default=Path('dist/VideoDownloader'))
    parser.add_argument('--output', type=Path, default=Path('dist/releases'))
    parser.add_argument('--smoke-report',type=Path,default=Path('logs/bundled-dependencies.json'))
    args = parser.parse_args()
    print(package_release(args.app, args.output, args.smoke_report))
