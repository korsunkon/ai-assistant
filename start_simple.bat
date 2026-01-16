@echo off
chcp 65001 >nul
cls

echo ═══════════════════════════════════════════════════════════════
echo   🚀 БЫСТРЫЙ ЗАПУСК - AI Ассистент Маркетолога
echo ═══════════════════════════════════════════════════════════════
echo.

REM Создание директорий
if not exist "data\audio" mkdir data\audio
if not exist "data\transcripts" mkdir data\transcripts
if not exist "data\results" mkdir data\results
if not exist "logs" mkdir logs

echo ✓ Запускаю оба сервера...
echo.

REM Запуск Backend в фоне
start /min "Backend" cmd /c "start_backend.bat"
echo ✓ Backend запущен (минимизировано)

REM Ожидание
timeout /t 8 /nobreak >nul

REM Запуск Frontend в фоне
start /min "Frontend" cmd /c "start_frontend.bat"
echo ✓ Frontend запущен (минимизировано)

echo.
echo ⏳ Подождите 5 секунд...
timeout /t 5 /nobreak >nul

echo.
echo ═══════════════════════════════════════════════════════════════
echo   ✓ ВСЁ ГОТОВО!
echo ═══════════════════════════════════════════════════════════════
echo.
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo.

REM Открытие браузера
start http://localhost:5173

echo ✓ Браузер открыт!
echo.
echo 📌 Серверы работают в фоновых окнах (минимизированы)
echo    Найдите их на панели задач если нужно посмотреть логи
echo.
echo ⚠️  Для остановки серверов:
echo    - Найдите окна "Backend" и "Frontend" на панели задач
echo    - Закройте их
echo.
pause
