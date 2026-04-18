@echo off
echo Starting Base Guias Unimed System...
echo Note: Please allow access in Firewall if prompted.


echo Starting Worker Server...
start "Worker Server 8001" cmd /k "set PORT=8001 && python Worker/server.py"
timeout /t 1

echo Starting Dispatcher...
start "Dispatcher" cmd /k "set API_SERVER_URLS=http://127.0.0.1:8001 && python Worker/dispatcher.py"
timeout /t 1


echo.
echo ========================================================
echo System Started!
echo ========================================================
echo.
pause
