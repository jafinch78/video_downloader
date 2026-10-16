# Compatible with Windows PowerShell 5.1. Logs both native output streams live.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Executable,
    [string[]]$ArgumentList = @(),
    [Parameter(Mandatory=$true)][string]$LogDirectory,
    [string]$TaskName = 'command'
)
$ErrorActionPreference = 'Stop'
$writer = $null
$exitCode = 1
$started = [DateTime]::UtcNow
try {
    New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    $unique = [Guid]::NewGuid().ToString('N').Substring(0,8)
    $safeName = $TaskName -replace '[^A-Za-z0-9_-]', '_'
    $logPath = Join-Path $LogDirectory "$safeName-$stamp-$unique.log"
    $summaryPath = [IO.Path]::ChangeExtension($logPath, '.json')
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [Console]::OutputEncoding = $utf8
    $OutputEncoding = $utf8
    $writer = New-Object System.IO.StreamWriter($logPath, $false, $utf8)
    $writer.AutoFlush = $true
    function Write-Recorded([string]$Text) {
        Write-Host $Text
        $writer.WriteLine($Text)
    }
    Write-Recorded "Task: $TaskName"
    Write-Recorded "Started UTC: $($started.ToString('o'))"
    Write-Recorded "Log: $logPath"
    Write-Recorded "PowerShell: $($PSVersionTable.PSVersion)"
    Get-Command -Name $Executable -CommandType Application -ErrorAction Stop | Out-Null
    # Native stderr is data to preserve, not a PowerShell terminating exception.
    $ErrorActionPreference = 'Continue'
    if (Test-Path variable:PSNativeCommandUseErrorActionPreference) {
        $PSNativeCommandUseErrorActionPreference = $false
    }
    $global:LASTEXITCODE = 1
    & $Executable @ArgumentList 2>&1 | ForEach-Object { Write-Recorded ([string]$_) }
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
} catch {
    $exitCode = 1
    $message = "Logger/launch ERROR: $($_.Exception.Message)"
    Write-Host $message
    if ($writer) { try { $writer.WriteLine($message) } catch {} }
} finally {
    $finished = [DateTime]::UtcNow
    $status = if ($exitCode -eq 0) { 'SUCCESS' } else { 'FAILED' }
    $footer = "$status | Exit code: $exitCode | Finished UTC: $($finished.ToString('o'))"
    Write-Host $footer
    if ($writer) {
        try {
            $writer.WriteLine($footer)
            $writer.Dispose()
            $summary = [ordered]@{
                task = $TaskName
                started_utc = $started.ToString('o')
                finished_utc = $finished.ToString('o')
                elapsed_seconds = ($finished - $started).TotalSeconds
                exit_code = $exitCode
                success = ($exitCode -eq 0)
                log_file = $logPath
            }
            [IO.File]::WriteAllText($summaryPath, ($summary | ConvertTo-Json), $utf8)
            Write-Host "Log saved: $logPath"
            Write-Host "Result JSON: $summaryPath"
        } catch {
            Write-Host "ERROR saving log/result: $($_.Exception.Message)"
            $exitCode = 1
        }
    }
}
exit $exitCode
