"""Copy installed dependency and runtime license texts into the portable folder."""
import hashlib
import shutil
import sys
from importlib.metadata import distribution
from pathlib import Path


def collect(output: Path, include_runtime=True):
    lock = Path(__file__).resolve().parents[1]/'requirements-lock.txt'
    output.mkdir(parents=True, exist_ok=True)
    for line in lock.read_text().splitlines():
        name=line.split('==')[0]
        dist=distribution(name)
        found=False
        for relative in dist.files or []:
            if any(part.lower() in ('licenses','license','copying') for part in relative.parts) or relative.name.lower().startswith(('license','copying','notice')):
                source=Path(dist.locate_file(relative))
                if source.is_file():
                    target=output/name/Path(*relative.parts)
                    target.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(source,target)
                    found=True
        if not found:
            raise ValueError(f'No packaged license text found for {name}; resolve before distribution.')
    if include_runtime:
        base=Path(sys.base_prefix)
        for name,source in [('Python',base/'LICENSE.txt'),('Tcl',base/'tcl/tcl8.6/license.terms'),('Tk',base/'tcl/tk8.6/license.terms')]:
            if name in ('Tcl', 'Tk') and not source.is_file():
                # CPython 3.12.7 Windows bundles Tcl/Tk 8.6.13 but does not
                # install these separate upstream notice files. Retain verified
                # copies so packaging remains offline and notices stay mandatory.
                source=Path(__file__).resolve().parents[1]/'packaging/licenses'/f'{name}-8.6.13.txt'
                expected={
                    'Tcl':'c0a69a2bfd757361ec7e6143973b103c90409316b49e9c88db26ad6388e79f16',
                    'Tk':'2cde822b93ca16ae535c954b7dfe658b4ad10df2a193628d1b358f1765e8b198',
                }[name]
                if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest()!=expected:
                    raise ValueError(f'Missing or altered bundled {name} 8.6.13 license: {source}')
                print(f'{name}: using verified bundled 8.6.13 license')
            if not source.is_file():
                raise ValueError(f'Cannot locate {name} runtime license at {source}')
            target=output/name/'LICENSE.txt'
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,target)


if __name__ == '__main__':
    collect(Path('dist/VideoDownloader/third-party-licenses'))
