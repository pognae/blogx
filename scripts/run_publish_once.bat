@echo off
setlocal
cd /d "%~dp0\.."
set PYTHONPATH=%CD%\src
py -m tistory_auto_publisher publish --config config.json
