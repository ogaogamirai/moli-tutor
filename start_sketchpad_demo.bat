@echo off
chcp 65001 >nul
setlocal
pushd "%~dp0"
set "PY=%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe"
if not exist "%PY%" set "PY=pythonw"
set PYTHONUTF8=1
echo Sketchpad 試読: 教材は demo-material\sketchpad\index.html
echo 起動後: python -X utf8 tutor_demo_sketchpad.py
start "Moli-Tutor (Sketchpad)" "%PY%" "%~dp0tutor_cockpit.py" --state "%~dp0tutor_state.json" --material-dir "%~dp0demo-material" --port 8777
popd
endlocal
