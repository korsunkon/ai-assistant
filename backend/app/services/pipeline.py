from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any

from sqlalchemy.orm import Session
from loguru import logger

from ..config import settings
from ..models import Call, Analysis, AnalysisResult
from .ollama_client import OllamaClient

try:
    import whisper  # type: ignore
except ImportError:  # pragma: no cover
    try:
        # Пробуем импортировать как openai-whisper
        from openai_whisper import whisper  # type: ignore
    except ImportError:
        whisper = None

_whisper_model = None


def _get_whisper_model():
    """
    Ленивая загрузка модели Whisper.
    Если библиотека не установлена — бросаем понятную ошибку.
    """
    global _whisper_model
    if _whisper_model is None:
        if whisper is None:
            raise RuntimeError(
                "Библиотека 'whisper' не установлена. "
                "Добавьте её в requirements.txt и установите зависимости."
            )
        _whisper_model = whisper.load_model(settings.whisper_model_name)
    return _whisper_model


def transcribe_call(call: Call) -> Dict[str, Any]:
    """
    Транскрибирует аудиофайл звонка с помощью локальной модели Whisper.
    Возвращает словарь с результатом (приближённо к формату Whisper).
    """
    logger.info(f"Начинаю транскрибацию звонка {call.id}: {call.filename}")
    model = _get_whisper_model()
    
    # Обрабатываем путь: если относительный - делаем абсолютным относительно data_root
    audio_path = Path(call.original_path)
    
    # Если путь не абсолютный или файл не найден, пытаемся найти его
    if not audio_path.is_absolute() or not audio_path.exists():
        # Сначала пробуем разрешить относительно data_root/audio
        audio_dir = settings.data_root / settings.audio_dir_name
        fallback_path = audio_dir / Path(call.original_path).name
        
        if fallback_path.exists():
            audio_path = fallback_path
            logger.info(f"Найден файл по fallback пути: {audio_path.absolute()}")
        elif audio_path.is_absolute() and not audio_path.exists():
            # Если абсолютный путь не работает, пробуем по имени файла
            fallback_path = audio_dir / call.filename
            if fallback_path.exists():
                audio_path = fallback_path
                logger.info(f"Найден файл по имени: {audio_path.absolute()}")
            else:
                error_msg = f"Аудиофайл не найден. Оригинальный путь: {call.original_path}, Имя файла: {call.filename}, Проверенные пути: {[audio_path, fallback_path]}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)
        elif not audio_path.is_absolute():
            # Пробуем сделать абсолютным
            audio_path = audio_path.absolute()
            if not audio_path.exists():
                # Последняя попытка - по имени файла в audio директории
                audio_path = audio_dir / call.filename
                if not audio_path.exists():
                    error_msg = f"Аудиофайл не найден. Оригинальный путь: {call.original_path}, Имя файла: {call.filename}"
                    logger.error(error_msg)
                    raise FileNotFoundError(error_msg)
    
    logger.info(f"Используемый путь к файлу: {audio_path.absolute()}")
    
    logger.info(f"Транскрибирую файл: {audio_path.absolute()}")
    try:
        # Используем librosa для загрузки аудио (обход проблемы с ffmpeg на Windows)
        try:
            import librosa
            import numpy as np
            
            # Загружаем аудио через librosa (16kHz - стандартная частота для Whisper)
            logger.info("Загружаю аудио через librosa...")
            audio_array, sr = librosa.load(str(audio_path.absolute()), sr=16000)
            audio_array = audio_array.astype(np.float32)
            
            # Передаём numpy array напрямую в Whisper
            logger.info(f"Аудио загружено: {len(audio_array)} сэмплов, частота {sr} Hz")
            result = model.transcribe(
                audio_array,
                language=settings.whisper_language,
                verbose=True,
            )
        except ImportError:
            # Если librosa не установлен, пробуем стандартный способ (требует ffmpeg)
            logger.warning("librosa не установлен, используем стандартный способ (требует ffmpeg)")
            result = model.transcribe(
                str(audio_path.absolute()),
                language=settings.whisper_language,
                verbose=True,
            )
        
        logger.info(f"Транскрибация завершена для звонка {call.id}")
        return result
    except Exception as e:
        logger.error(f"Ошибка при транскрибации звонка {call.id}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def save_transcript(call: Call, transcript: Dict[str, Any]) -> Path:
    """
    Сохраняет транскрипт в JSON-файл в директорию transcripts.
    """
    transcripts_dir = settings.data_root / settings.transcripts_dir_name
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    out_path = transcripts_dir / f"{call.id}.json"
    out_path.write_text(json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def simple_role_assignment(transcript: Dict[str, Any]) -> Dict[str, Any]:
    """
    Упрощённая \"диаризация\" и назначение ролей.
    На MVP мы считаем, что весь текст — один диалог без чётких границ спикеров.
    Возвращаем структуру с одним сегментом и ролями Клиент/Сотрудник по эвристике.
    """
    text = transcript.get("text", "") or ""
    segments = transcript.get("segments") or []

    # Если есть сегменты — соберём их текст
    if segments and not text:
        text = " ".join(seg.get("text", "") for seg in segments)

    # Для MVP просто считаем, что первый говорящий — сотрудник, второй — клиент,
    # но без настоящего деления на сегменты это в основном заглушка.
    return {
        "segments": [
            {
                "start": 0.0,
                "end": transcript.get("duration", 0.0),
                "speaker": "Сотрудник",
                "text": text,
            }
        ]
    }


def analyze_call_with_llm(
    call: Call,
    transcript_with_roles: Dict[str, Any],
    query_text: str,
) -> Dict[str, Any]:
    """
    Анализирует один звонок по пользовательскому запросу с помощью Qwen3:8b.
    """
    logger.info(f"Начинаю LLM-анализ звонка {call.id}")
    client = OllamaClient()

    segments = transcript_with_roles.get("segments", [])
    full_text = "\n".join(
        f"[{seg.get('speaker', 'Спикер')}] {seg.get('text', '')}" for seg in segments
    )

    if not full_text.strip():
        logger.warning(f"Пустой транскрипт для звонка {call.id}")
        return {"summary": "Пустой транскрипт", "findings": []}

    prompt = (
        "Ты аналитик звонков в контакт-центре. "
        "Тебе дан полный транскрипт звонка и исследовательский запрос от маркетолога.\n\n"
        "Транскрипт (с ролями спикеров):\n"
        f"{full_text}\n\n"
        "Запрос маркетолога:\n"
        f"{query_text}\n\n"
        "Ответь строго в формате JSON. Пример структуры:\n"
        "{\n"
        '  \"summary\": \"краткая выжимка по звонку\",\n'
        '  \"findings\": [\n'
        "    {\"criterion\": \"...\"," '"value": "..."," "evidence": ["цитата1", "цитата2"]}\n'
        "  ]\n"
        "}\n"
    )

    try:
        raw = client.generate(prompt, json_mode=True)
        logger.info(f"Получен ответ от LLM для звонка {call.id}")
    except Exception as e:
        logger.error(f"Ошибка при обращении к Ollama для звонка {call.id}: {str(e)}")
        raise

    try:
        parsed = json.loads(raw)
    except Exception as e:
        logger.warning(f"Ошибка парсинга JSON от модели для звонка {call.id}: {str(e)}")
        # Если модель вернула невалидный JSON — всё равно сохраним сырой текст.
        parsed = {"summary": "Ошибка парсинга JSON от модели", "raw": raw}

    return parsed


def run_analysis_for_call(
    db: Session,
    analysis: Analysis,
    call: Call,
    query_text: str,
) -> None:
    """
    Полный цикл обработки одного звонка в рамках исследования.
    """
    logger.info(f"Начинаю обработку звонка {call.id} для исследования {analysis.id}")
    
    try:
        # Обновляем статус на "processing"
        call.status = "processing"
        db.commit()
        
        # 1. Транскрибация
        transcript = transcribe_call(call)
        save_transcript(call, transcript)

        # 2. Упрощённая диаризация/назначение ролей
        transcript_with_roles = simple_role_assignment(transcript)

        # 3. LLM-анализ
        analysis_json = analyze_call_with_llm(call, transcript_with_roles, query_text)

        # 4. Сохранение результата
        summary = analysis_json.get("summary") or ""
        json_str = json.dumps(analysis_json, ensure_ascii=False)

        result = AnalysisResult(
            analysis_id=analysis.id,
            call_id=call.id,
            summary=summary,
            json_result=json_str,
        )
        db.add(result)
        
        # Обновляем статус на "processed"
        call.status = "processed"
        db.commit()
        logger.info(f"Успешно обработан звонок {call.id}")
    except Exception as e:
        logger.error(f"Критическая ошибка при обработке звонка {call.id}: {str(e)}")
        call.status = "error"
        db.rollback()
        db.commit()
        raise


