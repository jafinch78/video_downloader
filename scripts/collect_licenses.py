"""Copy installed dependency and runtime license texts into the portable folder."""
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
            if not source.is_file():
                raise ValueError(f'Cannot locate {name} runtime license at {source}')
            target=output/name/'LICENSE.txt'
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,target)


if __name__ == '__main__':
    collect(Path('dist/VideoDownloader/third-party-licenses'))
