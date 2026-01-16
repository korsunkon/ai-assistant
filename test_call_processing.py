#!/usr/bin/env python3
"""Тест обработки звонка"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from backend.app.db import SessionLocal
from backend.app.models import Call
from backend.app.services.pipeline import transcribe_call
from loguru import logger

logger.add("logs/test_call.log", level="DEBUG")

def test_call_processing():
    db = SessionLocal()
    try:
        call = db.query(Call).first()
        if not call:
            logger.error("Нет звонков в БД")
            return False
        
        logger.info(f"Тестирую звонок ID={call.id}, файл={call.filename}")
        logger.info(f"Путь в БД: {call.original_path}")
        
        try:
            result = transcribe_call(call)
            logger.info("Транскрибация успешна!")
            logger.info(f"Результат содержит текст: {'text' in result}")
            return True
        except Exception as e:
            logger.error(f"Ошибка транскрибации: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_call_processing()
    sys.exit(0 if success else 1)

