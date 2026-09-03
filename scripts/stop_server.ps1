# Stops whatever is listening on the app port (default 8000).
param([int]$Port = 8000)
$conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($conns) {
    $conns | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
        Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
        Write-Output "stopped PID $_"
    }
} else {
    Write-Output "nothing listening on port $Port"
}
