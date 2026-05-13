@echo off
setlocal
cd /d "%~dp0\.."
set PYTHONPATH=%CD%\src
py -m unittest discover -s tests -v %*
