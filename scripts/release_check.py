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
    require_native_target()
    exe = exe.resolve()
    if not exe.is_file():
        raise ValueError('The built Windows executable is missing.')
    tools = exe.parent/'_internal'/'assets'
    ffmpeg = tools/'ffmpeg.exe'
    ffprobe = tools/'ffprobe.exe'
    report = {'exe_sha256':sha256(exe), 'platform':platform.platform(), 'automated_pass':False,
              'manual_confirmed':manual_confirmed, 'release_ready':False}
    try:
        with tempfile.TemporaryDirectory(prefix='Video check 空 ') as temporary:
            root = Path(temporary)
            diagnostic = root/'diagnostic.json'
            subprocess.run([str(exe),'--diagnostic',str(diagnostic)],check=True,timeout=90)
            report['runtime']=json.loads(diagnostic.read_text(encoding='utf-8'))
            if report['runtime']['python'] != '3.12.7' or not report['runtime']['frozen'] or report['runtime']['bits'] != 64:
                raise ValueError('Wrong frozen runtime.')
            media=root/'media'
            media.mkdir()
            subprocess.run([str(ffmpeg),'-v','error','-f','lavfi','-i','color=size=64x64:rate=10:duration=2',
                '-f','lavfi','-i','sine=frequency=440:duration=2','-c:v','mpeg4','-c:a','aac','-shortest',
                '-f','dash',str(media/'sample.mpd')],check=True,timeout=60)
            class Quiet(http.server.SimpleHTTPRequestHandler):
                def log_message(self,*args):
                    pass
            server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(media)))
            thread=threading.Thread(target=server.serve_forever,daemon=True)
            thread.start()
            try:
                destination=root/'saved video 空'
                destination.mkdir()
                events=root/'events.jsonl'
                environment=os.environ.copy()
                environment['VIDEO_DOWNLOADER_EVENTS']=str(events)
                url=f'http://127.0.0.1:{server.server_port}/sample.mpd'
                subprocess.run([str(exe),'--worker','--url',url,'--destination',str(destination)],
                    check=True,timeout=120,env=environment)
                parsed=[json.loads(line) for line in events.read_text(encoding='utf-8').splitlines()]
                completions=[e for e in parsed if e.get('type')=='complete']
                if len(completions)!=1:
                    raise ValueError('Frozen worker did not report exactly one completed media file.')
                final=Path(completions[0]['path'])
                probe=subprocess.run([str(ffprobe),'-v','error','-show_streams','-of','json',str(final)],
                    check=True,capture_output=True,text=True,encoding='utf-8',timeout=30)
                types={s.get('codec_type') for s in json.loads(probe.stdout)['streams']}
                if not {'audio','video'} <= types:
                    raise ValueError('Frozen output is missing video or audio.')
                report['fixture_sha256']=sha256(final)
                report['automated_pass']=True
                report['release_ready']=bool(manual_confirmed)
            finally:
                server.shutdown()
                server.server_close()
                thread.join()
    except Exception as exc:
        report['error']=str(exc)
        raise
    finally:
        report_path.parent.mkdir(parents=True,exist_ok=True)
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
