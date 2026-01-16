@echo off
echo Запуск Backend...
if not exist .venv (
    echo Создание виртуального окружения...
    python -m venv .venv
)
call .venv\Scripts\activate
pip install -q -r requirements.txt
echo Backend запускается на http://localhost:8000
uvicorn backend.app.main:app --reload --port 8000
pause
