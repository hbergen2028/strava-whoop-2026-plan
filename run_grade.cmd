@echo off
cd /d "%~dp0"
py -3.12 fetch.py
py -3.12 whoop_fetch.py
py -3.12 grade.py
