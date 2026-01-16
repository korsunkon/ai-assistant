#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки настройки проекта
"""

import os
import sys
from pathlib import Path

def test_python_version():
    """Проверяет версию Python"""
    print("🐍 Проверка версии Python...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
        return True
    else:
        print(f"❌ Требуется Python 3.8+, у вас {version.major}.{version.minor}.{version.micro}")
        return False

def test_dependencies():
    """Проверяет установленные зависимости"""
    print("\n📦 Проверка зависимостей...")
    
    required_packages = ['openai', 'pandas', 'openpyxl']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} - установлен")
        except ImportError:
            print(f"❌ {package} - НЕ установлен")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Установите недостающие пакеты:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def test_directory_structure():
    """Проверяет структуру директорий"""
    print("\n📁 Проверка структуры проекта...")
    
    # Проверяем наличие основных файлов
    required_files = [
        'transcribe_calls.py',
        'advanced_transcriber.py',
        'requirements.txt',
        'README.md'
    ]
    
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file} - найден")
        else:
            print(f"❌ {file} - НЕ найден")
    
    # Проверяем папку calls
    if os.path.exists('calls'):
        print("✅ Папка 'calls' - найдена")
        
        # Проверяем MP3 файлы
        mp3_files = list(Path('calls').glob('*.mp3'))
        if mp3_files:
            print(f"✅ Найдено {len(mp3_files)} MP3 файлов:")
            for file in mp3_files:
                print(f"   - {file.name}")
        else:
            print("ℹ️  Папка 'calls' пуста. Поместите туда MP3 файлы для транскрибации.")
    else:
        print("❌ Папка 'calls' - НЕ найдена")
    
    return True

def test_api_key():
    """Проверяет наличие API ключа"""
    print("\n🔑 Проверка API ключа OpenAI...")
    
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        # Скрываем ключ для безопасности
        masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        print(f"✅ API ключ найден: {masked_key}")
        return True
    else:
        print("❌ API ключ НЕ найден")
        print("\n📋 Для установки API ключа:")
        print("Windows (PowerShell): $env:OPENAI_API_KEY='your_key_here'")
        print("Windows (CMD): set OPENAI_API_KEY=your_key_here")
        print("Linux/Mac: export OPENAI_API_KEY='your_key_here'")
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 Тестирование настройки проекта транскрибации звонков\n")
    
    tests = [
        test_python_version,
        test_dependencies,
        test_directory_structure,
        test_api_key
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Ошибка в тесте {test.__name__}: {e}")
    
    print(f"\n📊 Результаты тестирования: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 Все тесты пройдены! Проект готов к использованию.")
        print("\n📖 Следующие шаги:")
        print("1. Поместите MP3 файлы в папку 'calls'")
        print("2. Запустите: python advanced_transcriber.py")
    else:
        print("⚠️  Некоторые тесты не пройдены. Исправьте ошибки перед использованием.")
    
    return passed == total

if __name__ == "__main__":
    main() 