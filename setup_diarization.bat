@echo off
chcp 65001 >nul
echo ========================================
echo Настройка локальной модели диаризации
echo ========================================
echo.

:: Проверка git-lfs
where git-lfs >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Git LFS не установлен!
    echo.
    echo Установите Git LFS:
    echo 1. Скачайте: https://git-lfs.github.com/
    echo 2. Установите и запустите: git lfs install
    echo 3. Запустите этот скрипт снова
    pause
    exit /b 1
)

echo ✓ Git LFS установлен
echo.

:: Проверка наличия модели
if exist "speaker-diarization-3.1" (
    echo ✓ Модель уже скачана: speaker-diarization-3.1
    echo.
    goto :configure
)

echo Скачиваю модель с HuggingFace...
echo Это займет несколько минут (~500 МБ)
echo.
echo ВАЖНО: Для скачивания нужен HuggingFace аккаунт
echo 1. Зарегистрируйтесь: https://huggingface.co/join
echo 2. Примите условия: https://huggingface.co/pyannote/speaker-diarization-3.1
echo 3. Когда git попросит логин/пароль:
echo    - Username: ваш_логин_hf
echo    - Password: ваш_токен_hf (создайте на https://huggingface.co/settings/tokens)
echo.
pause

git clone https://huggingface.co/pyannote/speaker-diarization-3.1
if %errorlevel% neq 0 (
    echo.
    echo ❌ Ошибка при скачивании модели
    echo.
    echo Проверьте:
    echo 1. Есть ли интернет
    echo 2. Приняли ли вы условия на https://huggingface.co/pyannote/speaker-diarization-3.1
    echo 3. Правильно ли ввели токен
    pause
    exit /b 1
)

echo.
echo ✓ Модель успешно скачана!
echo.

:configure
echo Настраиваю config.py...
echo.

:: Проверка текущей конфигурации
findstr /C:"diarization_model" backend\app\config.py >nul
if %errorlevel% equ 0 (
    echo ✓ Конфигурация найдена в config.py
    echo.
    echo Убедитесь что в backend\app\config.py указан локальный путь:
    echo diarization_model: str = "./speaker-diarization-3.1"
) else (
    echo ⚠ Параметр diarization_model не найден в config.py
    echo.
    echo Добавьте в backend\app\config.py:
    echo diarization_model: str = "./speaker-diarization-3.1"
)

echo.
echo ========================================
echo ✓ ГОТОВО!
echo ========================================
echo.
echo Теперь диаризация работает полностью локально!
echo Токен HuggingFace больше не нужен при запуске.
echo.
echo Запустите приложение: start.bat
echo.
pause
