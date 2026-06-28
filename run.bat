@echo off
chcp 65001 >nul
REM 植物大战僵尸 (含无尽模式) 一键启动
REM 自动切到本文件所在目录，并用 Anaconda base 的 Python (已装好 pygame)
cd /d "%~dp0"
"C:\Users\ASUS\anaconda3\python.exe" main.py
pause
