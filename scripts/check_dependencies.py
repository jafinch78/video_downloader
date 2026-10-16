"""Run and print local dependency checks, retaining failure details in JSON."""
import argparse
import json
from pathlib import Path
from video_downloader.diagnostics import write_diagnostic


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('logs/local-dependencies.json'))
    args=parser.parse_args()
    try:
        write_diagnostic(args.output,check_gui=True)
    except Exception as exc:
        print(f'DEPENDENCY CHECK FAILED: {exc}',flush=True)
        print(f'Report: {args.output.resolve()}',flush=True)
        return 1
    data=json.loads(args.output.read_text(encoding='utf-8'))
    for item in data['dependencies']['packages']:
        print(f"PASS {item['name']} {item['version']} (module loaded)",flush=True)
    print(f"PASS native AES, native Brotli, TLS certificate store, Tcl {data['tkinter']['tcl']}, Tk {data['tkinter']['tk']}",flush=True)
    print(data['ffmpeg'],flush=True)
    print(data['ffprobe'],flush=True)
    print(f'DEPENDENCY CHECK PASS. Report: {args.output.resolve()}',flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
