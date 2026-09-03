# Starts the server fully detached; returns immediately.
# Logs: uvicorn.log / uvicorn.err.log   Stop: scripts/stop_server.ps1
$dir = Split-Path -Parent $PSScriptRoot
Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c", "`"$dir\serve.cmd`"" `
    -WorkingDirectory $dir -WindowStyle Hidden
