@echo off
echo Запуск Frontend...
cd frontend
if not exist node_modules (
    echo Установка зависимостей...
    call npm install
)
echo Frontend запускается на http://localhost:5173
call npm run dev
pause
