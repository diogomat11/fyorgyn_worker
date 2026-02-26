@echo off
echo =======================================
echo LIMPANDO TODOS OS SERVIDORES TRAVADOS
echo =======================================
echo.
echo Fechando processos Python (Backend/Workers)...
taskkill /F /IM python.exe /T 2>nul
echo.
echo Fechando processos Node (Frontend)...
taskkill /F /IM node.exe /T 2>nul
echo.
echo Limpeza concluida!
echo Agora voce pode abrir novos terminais para o Backend, Frontend e GUI limpos.
echo.
pause
