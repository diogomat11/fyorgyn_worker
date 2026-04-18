@echo off
cd /d "%~dp0"
echo Installing dependencies...
pip install -r requirements.txt
echo Cleaning up ghost browser sessions...
taskkill /F /IM chromedriver.exe /T 2>nul
taskkill /F /IM chrome.exe /T 2>nul
echo Starting GUI from source...
python gui.py
pause
