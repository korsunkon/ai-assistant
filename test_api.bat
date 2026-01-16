@echo off
echo ===============================================
echo Проверка работы Backend API
echo ===============================================
echo.

echo 1. Проверка health endpoint...
curl -s http://localhost:8000/health
echo.
echo.

echo 2. Проверка списка звонков...
curl -s http://localhost:8000/calls
echo.
echo.

echo 3. Проверка через API prefix...
curl -s http://localhost:8000/api/calls
echo.
echo.

echo ===============================================
echo Проверка завершена
echo ===============================================
echo.
echo Если вы видите {"status":"ok"} в пункте 1,
echo значит Backend работает правильно.
echo.
echo Если в пунктах 2 или 3 вы видите [] или список,
echo значит API звонков работает.
echo.
pause
