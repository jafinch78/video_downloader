"""Execute the built portable EXE and its dependencies; no Win1607 certification."""
import argparse
import functools
import http.server
import json
import os
import platform
import subprocess
import tempfile
import threading
from pathlib import Path
from scripts.build_support import sha256
from scripts.verify_delivery import verify_folder, bundle_inventory
from video_downloader.runtime import subprocess_options


def check_bundle(exe: Path, report_path: Path):
    exe = exe.resolve()
    tools = exe.parent/'_internal'/'assets'
    ffmpeg = tools/'ffmpeg.exe'
    ffprobe = tools/'ffprobe.exe'
    report = {'exe_sha256':sha256(exe) if exe.is_file() else None, 'platform':platform.platform(), 'automated_pass':False,
              'kind':'bundled-runtime-smoke', 'manual_confirmed':False, 'release_ready':False}
    try:
        print('Checking portable folder structure and bundled asset integrity...',flush=True)
        verify_folder(exe.parent)
        report['bundle_files']=bundle_inventory(exe.parent)
        environment=os.environ.copy()
        for name in ('PYTHONHOME','PYTHONPATH'):
            environment.pop(name,None)
        if os.name=='nt':
            system_root=Path(os.environ.get('SystemRoot',r'C:\Windows'))
            environment['PATH']=';'.join(map(str,[exe.parent,exe.parent/'_internal',system_root/'System32',system_root]))
        with tempfile.TemporaryDirectory(prefix='Video check 空 ') as temporary:
            root = Path(temporary)
            diagnostic = root/'diagnostic.json'
            print('Running the actual EXE dependency/GUI self-test with installed-Python paths removed...',flush=True)
            try:
                subprocess.run([str(exe),'--self-test',str(diagnostic)],check=True,timeout=90,env=environment,**subprocess_options())
            finally:
                if diagnostic.exists():
                    report['runtime']=json.loads(diagnostic.read_text(encoding='utf-8'))
            if report['runtime']['python'] != '3.12.7' or not report['runtime']['frozen'] or report['runtime']['bits'] != 64:
                raise ValueError('Wrong frozen runtime.')
            if not report['runtime'].get('passed') or not report['runtime'].get('tkinter',{}).get('passed'):
                raise ValueError('Bundled dependency or Tcl/Tk self-test did not pass.')
            print('Bundled runtime, package imports, native libraries, certificates and Tk PASS.',flush=True)
            media=root/'media'
            media.mkdir()
            print('Generating a local audio/video fixture using the bundled FFmpeg...',flush=True)
            subprocess.run([str(ffmpeg),'-v','error','-f','lavfi','-i','color=size=64x64:rate=10:duration=2',
                '-f','lavfi','-i','sine=frequency=440:duration=2','-c:v','mpeg4','-c:a','aac','-shortest',
                '-f','dash','sample.mpd'],cwd=media,check=True,timeout=60)
            if len(list(media.glob('init-stream*.m4s')))<2 or len(list(media.glob('chunk-stream*.m4s')))<2:
                raise ValueError('DASH fixture fragments were not generated inside the HTTP-served media folder.')
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
                environment['VIDEO_DOWNLOADER_EVENTS']=str(events)
                url=f'http://127.0.0.1:{server.server_port}/sample.mpd'
                print('Downloading and merging the local fixture with the frozen worker...',flush=True)
                parsed=[]
                try:
                    subprocess.run([str(exe),'--worker','--url',url,'--destination',str(destination)],
                        check=True,timeout=120,env=environment)
                finally:
                    if events.exists():
                        for line in events.read_text(encoding='utf-8').splitlines():
                            try:
                                event=json.loads(line)
                                parsed.append(event)
                                if event.get('type') in ('status','error'):
                                    print(event.get('message',''),flush=True)
                            except (ValueError,AttributeError):
                                pass
                    report['worker_events']=[event for event in parsed if isinstance(event,dict) and event.get('type')!='progress']
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
                if report['bundle_files']!=bundle_inventory(exe.parent):
                    raise ValueError('The bundle changed during dependency/media checks.')
                report['automated_pass']=True
                report['release_ready']=False
                print('BUNDLED DEPENDENCY/MEDIA SMOKE PASS. Windows 1607 compatibility is not certified by this check.',flush=True)
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


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe',type=Path,default=Path('dist/VideoDownloader/VideoDownloader.exe'))
    parser.add_argument('--report',type=Path,default=Path('logs/bundled-dependencies.json'))
    args=parser.parse_args()
    try:
        check_bundle(args.exe,args.report)
    except Exception as exc:
        print(f'BUNDLED CHECK FAILED: {exc}. Report: {args.report.resolve()}',flush=True)
        raise SystemExit(1)
