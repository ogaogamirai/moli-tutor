@echo off
chcp 65001 >nul
setlocal
pushd "%~dp0"
set "PY=%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe"
if not exist "%PY%" set "PY=pythonw"
set PYTHONUTF8=1
echo 数学可視化ギャラリー — 右ペイン b9 推奨
echo   python -X utf8 tutor_demo_math_viz.py --once
start "Moli-Tutor (Math Viz)" "%PY%" "%~dp0tutor_cockpit.py" --state "%~dp0tutor_state.json" --material-dir "%~dp0demo-material" --port 8777
popd
endlocal
