@echo off
echo Starting 5 Workers and Dispatcher in background...
start "Worker 9000" /B cmd /c "set PORT=9000&&set SGUCARD_HEADLESS=true&&python Worker/server.py"
start "Worker 9001" /B cmd /c "set PORT=9001&&set SGUCARD_HEADLESS=true&&python Worker/server.py"
start "Worker 9002" /B cmd /c "set PORT=9002&&set SGUCARD_HEADLESS=true&&python Worker/server.py"
start "Worker 9003" /B cmd /c "set PORT=9003&&set SGUCARD_HEADLESS=true&&python Worker/server.py"
start "Worker 9004" /B cmd /c "set PORT=9004&&set SGUCARD_HEADLESS=true&&python Worker/server.py"
ping 127.0.0.1 -n 4 >nul
start "Dispatcher" /B cmd /c "set API_SERVER_URLS=http://127.0.0.1:9000,http://127.0.0.1:9001,http://127.0.0.1:9002,http://127.0.0.1:9003,http://127.0.0.1:9004&&python Worker/dispatcher.py"
echo Workers started!
