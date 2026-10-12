@echo off
setlocal
pushd "%~dp0"
set "PY=%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe"
if not exist "%PY%" set "PY=pythonw"
set PYTHONUTF8=1
set "MAT=G:\マイドライブ\Projects\Teaching-materials\tropical-math"
powershell -NoProfile -Command "$c = Get-NetTCPConnection -LocalPort 8777 -State Listen -ErrorAction SilentlyContinue; if ($c) { $c | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue } }"
start "Moli-Tutor-Browser" "%PY%" "%~dp0tutor_cockpit.py" --browser --state "%~dp0tutor_state.json" --material-dir "%MAT%" --port 8777
popd
endlocal
