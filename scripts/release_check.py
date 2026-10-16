"""Automated gates for the exact Windows 1607 portable EXE, not a source substitute."""
import argparse
import functools
import http.server
import json
import os
import platform
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from scripts.build_support import sha256


def require_native_target(system=None, build=None):
    system = system or platform.system()
    if build is None:
        build = sys.getwindowsversion().build if system == 'Windows' else 0
    if system != 'Windows' or build != 14393:
        raise ValueError('Release validation must run on native Windows 10 1607 build 14393 x64.')


def check(exe: Path, report_path: Path, manual_confirmed=False):
    from scripts.bundle_check import check_bundle
    try:
        require_native_target()
    except Exception as exc:
        report_path.parent.mkdir(parents=True,exist_ok=True)
        report_path.write_text(json.dumps({'automated_pass':False,'release_ready':False,'error':str(exc)},indent=2)+'\n',encoding='utf-8')
        raise
    report=check_bundle(exe,report_path)
    report['kind']='native-win1607-validation'
    report['manual_confirmed']=bool(manual_confirmed)
    report['release_ready']=bool(manual_confirmed)
    report_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe',type=Path,default=Path('dist/VideoDownloader/VideoDownloader.exe'))
    parser.add_argument('--report',type=Path,default=Path('dist/validation-win1607.json'))
    parser.add_argument('--manual-confirmed',action='store_true',help='Attest that all manual README release checks were actually completed')
    args=parser.parse_args()
    result=check(args.exe,args.report,args.manual_confirmed)
    print('Automated frozen-media check passed. '+('Manual checks attested.' if result['release_ready'] else 'Manual GUI/offline/playback/cancellation checks remain.'))
