param([string]$JobId = '20261119-212241-607ce2dfab', [int]$Minutes = 120)
$ErrorActionPreference = 'SilentlyContinue'
$log = Join-Path $PSScriptRoot 'watch_shorts.log'
"$(Get-Date -Format o) monitor started for $JobId" | Out-File -Append -Encoding utf8 $log
for ($i = 0; $i -lt $Minutes; $i++) {
    Start-Sleep -Seconds 60
    try {
        $j = Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/jobs/$JobId" -TimeoutSec 10
        $done = @($j.clips | Where-Object { $_.status -eq 'done' }).Count
        $line = "{0} status={1} stage={2} progress={3:N3} clips={4}/{5} words={6} blocks={7}" -f `
            (Get-Date -Format o), $j.status, $j.stage, $j.progress, $done, @($j.clips).Count, $j.word_count, $j.done_blocks
        $line | Out-File -Append -Encoding utf8 $log
        Write-Output $line
        if ($j.status -in @('done', 'error', 'paused')) {
            "TERMINAL_STATUS=$($j.status)" | Out-File -Append -Encoding utf8 $log
            Write-Output "TERMINAL_STATUS=$($j.status)"
            if ($j.error) { Write-Output "ERROR=$($j.error)" }
            foreach ($c in $j.clips) {
                Write-Output ("CLIP {0} {1} {2}-{3} score={4} file={5}" -f $c.id, $c.status, $c.start, $c.end, $c.score, $c.file)
            }
            exit 0
        }
    } catch {
        "$(Get-Date -Format o) poll failed: $($_.Exception.Message)" | Out-File -Append -Encoding utf8 $log
    }
}
"MONITOR TIMED OUT after $Minutes minutes" | Out-File -Append -Encoding utf8 $log
Write-Output "MONITOR TIMED OUT"
