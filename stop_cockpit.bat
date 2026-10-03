@echo off
chcp 65001 >nul
setlocal
echo Moli-Tutor (port 8777) のプロセスを終了します…
powershell -NoProfile -Command ^
  "$c = Get-NetTCPConnection -LocalPort 8777 -State Listen -ErrorAction SilentlyContinue; " ^
  "if (-not $c) { Write-Host '  8777 で待ち受けしているプロセスはありません。'; exit 0 }; " ^
  "$c | ForEach-Object { $p = $_.OwningProcess; Write-Host ('  PID ' + $p); Stop-Process -Id $p -Force -ErrorAction SilentlyContinue }"
echo 完了。start_cockpit.bat で再起動してください。
endlocal
pause
