from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any

from sqlalchemy.orm import Session
from loguru import logger

from ..config import settings
from ..models import Call, Analysis, AnalysisResult
from .ollama_client import OllamaClient
from .diarization import perform_diarization, merge_transcription_with_diarization, DIARIZATION_AVAILABLE
from .role_assignment import assign_roles_with_llm
from .audio_preprocessing import preprocess_audio, cleanup_preprocessed_file, is_ffmpeg_available

try:
    from faster_whisper import WhisperModel
    import torch
    FASTER_WHISPER_AVAILABLE = True
    logger.info("faster-whisper обнаружен - будет использоваться для GPU ускорения")
except ImportError:  # pragma: no cover
    FASTER_WHISPER_AVAILABLE = False
    try:
        import whisper  # type: ignore
    except ImportError:
        try:
            from openai_whisper import whisper  # type: ignore
        except ImportError:
            whisper = None

_whisper_model = None


def _get_whisper_model():
    """
    Ленивая загрузка модели Whisper.
    Использует faster-whisper для GPU ускорения если доступен,
    иначе стандартный openai-whisper.
    """
    global _whisper_model
    if _whisper_model is None:
        if FASTER_WHISPER_AVAILABLE:
            # Используем faster-whisper с GPU
            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"

            logger.info(f"Загрузка faster-whisper модели '{settings.whisper_model_name}' на {device} (compute_type={compute_type})")
            _whisper_model = WhisperModel(
                settings.whisper_model_name,
                device=device,
                compute_type=compute_type,
                download_root=None  # Использует кэш HuggingFace
            )
            logger.info(f"faster-whisper модель загружена на {device}")
        else:
            # Fallback на стандартный whisper
            if whisper is None:
                raise RuntimeError(
                    "Библиотека 'whisper' или 'faster-whisper' не установлена. "
                    "Добавьте её в requirements.txt и установите зависимости."
                )
            logger.info(f"Загрузка openai-whisper модели '{settings.whisper_model_name}'")
            _whisper_model = whisper.load_model(settings.whisper_model_name)
    return _whisper_model


def transcribe_call(call: Call, audio_path: Path | None = None) -> Dict[str, Any]:
    """
    Транскрибирует аудиофайл звонка с помощью локальной модели Whisper.
    Возвращает словарь с результатом (приближённо к формату Whisper).

    Args:
        call: Объект звонка
        audio_path: Путь к аудиофайлу (если None - определяется автоматически)
    """
    logger.info(f"Начинаю транскрибацию звонка {call.id}: {call.filename}")
    model = _get_whisper_model()

    # Определяем путь к аудио если не передан
    if audio_path is None:
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

    # Предобработка аудио (нормализация, компрессия, шумоподавление)
    preprocessed_path = None
    transcribe_path = audio_path

    if settings.audio_preprocessing_enabled and is_ffmpeg_available():
        try:
            logger.info("Этап предобработки: нормализация, компрессия, шумоподавление")
            preprocessed_path = preprocess_audio(
                audio_path,
                normalize=settings.audio_normalize,
                compress=settings.audio_compress,
                denoise=settings.audio_denoise,
                highpass=settings.audio_highpass,
                highpass_freq=settings.audio_highpass_freq,
            )
            transcribe_path = preprocessed_path
            logger.info(f"Аудио предобработано: {preprocessed_path}")
        except Exception as e:
            logger.warning(f"Ошибка предобработки аудио, используем оригинал: {e}")
            preprocessed_path = None
            transcribe_path = audio_path
    elif settings.audio_preprocessing_enabled and not is_ffmpeg_available():
        logger.warning("Предобработка включена, но FFmpeg не найден. Используем оригинальный файл.")
    
    logger.info(f"Транскрибирую файл: {transcribe_path.absolute()}")
    try:
        if FASTER_WHISPER_AVAILABLE:
            # faster-whisper использует другой API
            logger.info("Используется faster-whisper для транскрипции")
            segments, info = model.transcribe(
                str(transcribe_path.absolute()),
                language=settings.whisper_language,
                beam_size=5,
                vad_filter=True,  # Voice Activity Detection для лучшего качества
                vad_parameters=dict(min_silence_duration_ms=500)
            )

            logger.info(f"Транскрипция: язык={info.language}, вероятность={info.language_probability:.2f}")

            # Конвертируем в формат совместимый с openai-whisper
            result_segments = []
            full_text = []

            for segment in segments:
                result_segments.append({
                    "id": segment.id,
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                    "tokens": segment.tokens,
                    "temperature": segment.temperature,
                    "avg_logprob": segment.avg_logprob,
                    "compression_ratio": segment.compression_ratio,
                    "no_speech_prob": segment.no_speech_prob
                })
                full_text.append(segment.text)

            result = {
                "text": " ".join(full_text),
                "segments": result_segments,
                "language": info.language
            }
        else:
            # Используем librosa для загрузки аудио (обход проблемы с ffmpeg на Windows)
            try:
                import librosa
                import numpy as np

                # Загружаем аудио через librosa (16kHz - стандартная частота для Whisper)
                logger.info("Загружаю аудио через librosa...")
                audio_array, sr = librosa.load(str(transcribe_path.absolute()), sr=16000)
                audio_array = audio_array.astype(np.float32)

                # Передаём numpy array напрямую в Whisper
                logger.info(f"Аудио загружено: {len(audio_array)} сэмплов, частота {sr} Hz")
                result = model.transcribe(
                    audio_array,
                    language=settings.whisper_language,
                    verbose=False,  # Отключено из-за проблем с Unicode в Windows консоли
                )
            except ImportError:
                # Если librosa не установлен, пробуем стандартный способ (требует ffmpeg)
                logger.warning("librosa не установлен, используем стандартный способ (требует ffmpeg)")
                result = model.transcribe(
                    str(transcribe_path.absolute()),
                    language=settings.whisper_language,
                    verbose=False,  # Отключено из-за проблем с Unicode в Windows консоли
                )

        logger.info(f"Транскрибация завершена для звонка {call.id}")
        return result
    except Exception as e:
        logger.error(f"Ошибка при транскрибации звонка {call.id}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
    finally:
        # Удаляем временный обработанный файл
        if preprocessed_path is not None:
            cleanup_preprocessed_file(preprocessed_path)


def save_transcript(call: Call, transcript: Dict[str, Any]) -> Path:
    """
    Сохраняет транскрипт в JSON-файл в директорию transcripts.
    """
    transcripts_dir = settings.data_root / settings.transcripts_dir_name
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    out_path = transcripts_dir / f"{call.id}.json"
    out_path.write_text(json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def perform_diarization_and_role_assignment(
    call: Call,
    transcript: Dict[str, Any],
    audio_path: Path
) -> Dict[str, Any]:
    """
    Выполняет полноценную диаризацию и определение ролей.

    Этапы:
    1. Диаризация аудио (определение кто и когда говорил)
    2. Объединение транскрипции с диаризацией
    3. Определение ролей через Qwen (Клиент/Сотрудник/etc)

    Args:
        call: Объект звонка из БД
        transcript: Результат транскрипции от Whisper
        audio_path: Путь к аудиофайлу

    Returns:
        Транскрипт с информацией о спикерах и их ролях
    """
    # Проверяем, включена ли диаризация
    if not settings.diarization_enabled:
        logger.info("Диаризация отключена в настройках, используется fallback")
        return simple_role_assignment(transcript)

    # Проверяем доступность библиотеки
    if not DIARIZATION_AVAILABLE:
        logger.warning("Библиотека диаризации недоступна, используется fallback")
        return simple_role_assignment(transcript)

    try:
        # Шаг 1: Диаризация
        logger.info(f"Выполняю диаризацию для звонка {call.id}")
        diarization_result = perform_diarization(
            audio_path,
            min_speakers=settings.min_speakers,
            max_speakers=settings.max_speakers
        )

        logger.info(
            f"Диаризация завершена: {diarization_result['num_speakers']} говорящих"
        )

        # Шаг 2: Объединение транскрипции с диаризацией
        transcript_with_speakers = merge_transcription_with_diarization(
            transcript, diarization_result
        )

        # Шаг 3: Определение ролей через LLM
        if settings.role_assignment_enabled:
            logger.info("Определяю роли говорящих через Qwen")
            transcript_with_roles = assign_roles_with_llm(transcript_with_speakers)
        else:
            logger.info("Определение ролей отключено, используются SPEAKER_XX")
            # Добавляем базовые роли (просто повторяем speaker)
            segments = []
            for seg in transcript_with_speakers.get("segments", []):
                segments.append({
                    **seg,
                    "role": seg.get("speaker", "Unknown")
                })
            transcript_with_roles = {
                **transcript_with_speakers,
                "segments": segments
            }

        return transcript_with_roles

    except Exception as e:
        logger.error(f"Ошибка при диаризации/определении ролей: {e}")
        logger.info("Используем fallback режим")
        return simple_role_assignment(transcript)


def simple_role_assignment(transcript: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fallback: Упрощённое назначение ролей без диаризации.
    Используется если диаризация недоступна или отключена.
    """
    text = transcript.get("text", "") or ""
    segments = transcript.get("segments") or []

    # Если есть сегменты — соберём их текст
    if segments and not text:
        text = " ".join(seg.get("text", "") for seg in segments)

    # Простая заглушка: все реплики от одного "Сотрудника"
    return {
        "text": text,
        "segments": [
            {
                "start": 0.0,
                "end": transcript.get("duration", 0.0),
                "speaker": "SPEAKER_00",
                "speaker_id": 0,
                "role": "Сотрудник",
                "text": text,
            }
        ],
        "speakers": ["SPEAKER_00"],
        "num_speakers": 1,
        "speaker_roles": {"SPEAKER_00": "Сотрудник"}
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


def load_existing_transcript(call: Call) -> Dict[str, Any] | None:
    """
    Загружает существующий транскрипт звонка если он есть.

    Returns:
        Транскрипт или None если файл не существует
    """
    transcripts_dir = settings.data_root / settings.transcripts_dir_name
    transcript_path = transcripts_dir / f"{call.id}.json"

    if transcript_path.exists():
        try:
            return json.loads(transcript_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Не удалось загрузить транскрипт для {call.id}: {e}")
            return None
    return None


def run_analysis_for_call(
    db: Session,
    analysis: Analysis,
    call: Call,
    query_text: str,
    force_retranscribe: bool = False,
) -> None:
    """
    Полный цикл обработки одного звонка в рамках исследования.

    Включает:
    1. Транскрибацию (Whisper) - пропускается если транскрипт уже есть
    2. Диаризацию (pyannote.audio) - пропускается если транскрипт уже есть
    3. Определение ролей (Qwen) - пропускается если транскрипт уже есть
    4. LLM-анализ (Qwen)

    Args:
        force_retranscribe: Если True - принудительно транскрибировать заново
    """
    logger.info(f"Начинаю обработку звонка {call.id} для исследования {analysis.id}")
    from datetime import datetime

    try:
        # Обновляем статус на "processing"
        call.status = "processing"
        db.commit()

        # Определяем путь к аудиофайлу (нужен для диаризации)
        audio_path = Path(call.original_path)
        if not audio_path.is_absolute() or not audio_path.exists():
            audio_dir = settings.data_root / settings.audio_dir_name
            audio_path = audio_dir / call.filename
            if not audio_path.exists():
                raise FileNotFoundError(f"Аудиофайл не найден: {audio_path}")

        # Проверяем, есть ли уже транскрипт
        existing_transcript = None
        if not force_retranscribe and call.has_transcript:
            existing_transcript = load_existing_transcript(call)
            if existing_transcript:
                logger.info(f"Используем существующий транскрипт для звонка {call.id}")

        if existing_transcript:
            # Используем существующий транскрипт
            transcript_with_roles = existing_transcript
            logger.info("Этапы 1-2/4: Пропущены (транскрипт уже есть)")
        else:
            # 1. Транскрибация
            logger.info("Этап 1/4: Транскрибация")
            transcript = transcribe_call(call)
            save_transcript(call, transcript)

            # 2. Диаризация + определение ролей
            logger.info("Этап 2/4: Диаризация и определение ролей")
            transcript_with_roles = perform_diarization_and_role_assignment(
                call, transcript, audio_path
            )

            # Сохраняем обогащенный транскрипт (с ролями)
            save_transcript(call, transcript_with_roles)

            # Обновляем флаг has_transcript
            call.has_transcript = True
            call.transcript_updated_at = datetime.utcnow()

        # 3. LLM-анализ
        logger.info("Этап 3/4: LLM-анализ")
        analysis_json = analyze_call_with_llm(call, transcript_with_roles, query_text)

        # 4. Сохранение результата
        logger.info("Этап 4/4: Сохранение результатов")
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
        logger.info(f"✓ Успешно обработан звонок {call.id}")
        logger.info(
            f"  - Говорящих: {transcript_with_roles.get('num_speakers', 'N/A')}"
        )
        logger.info(
            f"  - Роли: {transcript_with_roles.get('speaker_roles', {})}"
        )

    except Exception as e:
        logger.error(f"Критическая ошибка при обработке звонка {call.id}: {str(e)}")
        call.status = "error"
        db.rollback()
        db.commit()
        raise


