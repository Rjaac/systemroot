@echo off
chcp 65001 >nul
python "%~dp0_generator\manage.py" %*
