#!/usr/bin/env python3
"""Тестовый скрипт для проверки работы пайплайна"""

import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from backend.app.db import SessionLocal
from backend.app.models import Call
from backend.app.services.pipeline import _get_whisper_model, transcribe_call
from loguru import logger

logger.add("logs/test.log", level="DEBUG")

def test_whisper():
    """Тест импорта и загрузки модели Whisper"""
    try:
        logger.info("Тест 1: Импорт whisper...")
        import whisper
        logger.info(f"✓ Whisper импортирован: {whisper.__file__}")
        
        logger.info("Тест 2: Загрузка модели...")
        model = _get_whisper_model()
        logger.info(f"✓ Модель загружена: {type(model)}")
        
        return True
    except Exception as e:
        logger.error(f"✗ Ошибка: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_ollama():
    """Тест подключения к Ollama"""
    try:
        logger.info("Тест 3: Подключение к Ollama...")
        from backend.app.services.ollama_client import OllamaClient
        
        client = OllamaClient()
        test_prompt = "Скажи 'привет' одним словом"
        result = client.generate(test_prompt)
        logger.info(f"✓ Ollama ответил: {result[:50]}...")
        return True
    except Exception as e:
        logger.error(f"✗ Ошибка Ollama: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("Тестирование компонентов пайплайна")
    logger.info("=" * 50)
    
    results = []
    results.append(("Whisper", test_whisper()))
    results.append(("Ollama", test_ollama()))
    
    logger.info("=" * 50)
    logger.info("Результаты тестирования:")
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{name}: {status}")
    
    if all(r[1] for r in results):
        logger.info("Все тесты пройдены успешно!")
        sys.exit(0)
    else:
        logger.error("Некоторые тесты не пройдены!")
        sys.exit(1)

