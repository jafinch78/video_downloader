import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PWSH=os.environ.get('VIDEO_TEST_POWERSHELL') or shutil.which('pwsh') or shutil.which('powershell.exe')
if not PWSH:
    portable=Path(__file__).resolve().parents[1]/'.cloud-tools/powershell/pwsh'
    PWSH=str(portable) if portable.is_file() else None

@unittest.skipUnless(PWSH,'PowerShell required for real logger execution tests')
class LoggingTests(unittest.TestCase):
    def run_logged(self,exit_code,legacy=False):
        with tempfile.TemporaryDirectory(prefix='logs with space ') as directory:
            root=Path(directory)
            helper=Path('scripts/log_command.ps1').resolve()
            quote=lambda value: "'"+str(value).replace("'","''")+"'"
            code=f'import sys; print("stdout-marker",flush=True); print("Unicode-marker-空",flush=True); print("stderr-marker",file=sys.stderr,flush=True); sys.exit({exit_code})'
            native_script=root/'fixture script.py'
            native_script.write_text(code,encoding='utf-8')
            harness=root/'harness.ps1'
            prefix="$PSNativeCommandArgumentPassing='Legacy'\n" if legacy else ''
            harness.write_text(prefix+f'& {quote(helper)} -Executable {quote(sys.executable)} -ArgumentList @({quote(native_script)}) -LogDirectory {quote(root/"logs")} -TaskName test\nexit $LASTEXITCODE\n',encoding='utf-8-sig')
            environment=os.environ.copy()
            environment['XDG_CACHE_HOME']=str(root/'cache')
            environment['XDG_CONFIG_HOME']=str(root/'config')
            environment['XDG_DATA_HOME']=str(root/'data')
            environment['PYTHONUTF8']='1'
            result=subprocess.run([PWSH,'-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',str(harness)],capture_output=True,text=True,timeout=30,env=environment)
            self.assertEqual(result.returncode,exit_code,result.stdout+result.stderr)
            logs=list((root/'logs').glob('*.log'))
            self.assertEqual(len(logs),1,result.stdout+result.stderr)
            content=logs[0].read_text(encoding='utf-8-sig')
            self.assertIn('stdout-marker',content)
            self.assertIn('stderr-marker',content)
            self.assertIn('Unicode-marker-空',content)
            self.assertIn('SUCCESS' if exit_code==0 else 'FAILED',content)
            self.assertIn(f'Exit code: {exit_code}',content)
            summary=json.loads(logs[0].with_suffix('.json').read_text(encoding='utf-8-sig'))
            self.assertEqual(summary['exit_code'],exit_code)
            self.assertEqual(summary['success'],exit_code==0)
            self.assertIn('stdout-marker',result.stdout)
    def test_success_logs_both_streams(self):
        self.run_logged(0)
    def test_failure_preserves_nonzero_exit_and_logs(self):
        self.run_logged(7)

    def test_legacy_windows_powershell_argument_mode(self):
        self.run_logged(0,legacy=True)
        self.run_logged(7,legacy=True)
