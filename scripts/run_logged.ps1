[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidateSet('Build','Validate')][string]$Task,
    [switch]$ManualConfirmed
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$batch = if ($Task -eq 'Build') { 'BUILD_WINDOWS_EXE.bat' } else { 'RELEASE_CHECKLIST_WIN1607.bat' }
$path = Join-Path $root $batch
$extra = if ($ManualConfirmed) { ' --manual-confirmed' } else { '' }
# /s /c strips the outside quotes, retaining the quoted BAT path, including spaces.
$command = '""' + $path + '" --internal-run' + $extra + '"'
& (Join-Path $PSScriptRoot 'log_command.ps1') -Executable $env:ComSpec -ArgumentList @('/d','/v:off','/s','/c',$command) -LogDirectory (Join-Path $root 'logs') -TaskName ($Task.ToLowerInvariant())
exit $LASTEXITCODE
