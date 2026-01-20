"""
Модуль диаризации (определение говорящих) с использованием pyannote.audio
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Tuple
from loguru import logger

try:
    from pyannote.audio import Pipeline
    import torch
    DIARIZATION_AVAILABLE = True
except ImportError:
    DIARIZATION_AVAILABLE = False
    logger.warning("pyannote.audio не установлен. Диаризация недоступна.")

from ..config import settings

_diarization_pipeline = None


def _get_diarization_pipeline():
    """
    Ленивая загрузка pipeline диаризации.
    Загружается только при первом использовании.

    Поддерживает два режима:
    1. Локальная модель (если settings.diarization_model - путь к папке)
    2. Загрузка с HuggingFace (требует токен только при первой загрузке)
    """
    global _diarization_pipeline

    if _diarization_pipeline is None:
        if not DIARIZATION_AVAILABLE:
            raise RuntimeError(
                "pyannote.audio не установлен. "
                "Установите: pip install pyannote.audio torch torchaudio"
            )

        logger.info(f"Загружаю модель диаризации: {settings.diarization_model}")

        # Проверяем, является ли model_name локальным путем
        model_path = Path(settings.diarization_model)
        is_local = model_path.exists() and model_path.is_dir()

        try:
            if is_local:
                # Загружаем из локальной папки (не требует токен)
                logger.info(f"Загрузка локальной модели из: {model_path.absolute()}")
                _diarization_pipeline = Pipeline.from_pretrained(
                    str(model_path.absolute())
                )
            else:
                # Загружаем с HuggingFace (требует токен)
                logger.info("Загрузка модели с HuggingFace (требуется токен)")
                _diarization_pipeline = Pipeline.from_pretrained(
                    settings.diarization_model,
                    use_auth_token=True  # Использует токен из HF_TOKEN env var
                )

            # Переносим на GPU если доступен
            if torch.cuda.is_available():
                _diarization_pipeline.to(torch.device("cuda"))
                logger.info("Диаризация будет выполняться на GPU")
            else:
                logger.info("Диаризация будет выполняться на CPU")

        except Exception as e:
            logger.error(f"Ошибка загрузки модели диаризации: {e}")

            if not is_local:
                logger.info(
                    "РЕШЕНИЕ 1 (Рекомендуется): Скачать модель локально один раз\n"
                    "-----------------------------------------------------------\n"
                    "1. Установите git-lfs: https://git-lfs.github.com/\n"
                    "2. Клонируйте модель:\n"
                    "   git clone https://huggingface.co/pyannote/speaker-diarization-3.1\n"
                    "3. В config.py укажите путь к папке:\n"
                    "   diarization_model = './speaker-diarization-3.1'\n"
                    "4. После этого токен не нужен!\n\n"
                    "РЕШЕНИЕ 2: Использовать HuggingFace токен\n"
                    "-------------------------------------------\n"
                    "1. Зарегистрируйтесь: https://huggingface.co\n"
                    "2. Создайте токен: https://huggingface.co/settings/tokens\n"
                    "3. Примите условия: https://huggingface.co/pyannote/speaker-diarization-3.1\n"
                    "4. Установите: set HF_TOKEN=your_token"
                )
            raise

    return _diarization_pipeline


def perform_diarization(
    audio_path: str | Path,
    min_speakers: int | None = None,
    max_speakers: int | None = None
) -> Dict[str, Any]:
    """
    Выполняет диаризацию (определение говорящих) для аудиофайла.

    Args:
        audio_path: Путь к аудиофайлу
        min_speakers: Минимальное количество говорящих (None = автоопределение)
        max_speakers: Максимальное количество говорящих (None = автоопределение)

    Returns:
        Словарь с результатами диаризации:
        {
            "segments": [
                {
                    "start": 0.5,
                    "end": 3.2,
                    "speaker": "SPEAKER_00",
                    "speaker_id": 0
                },
                ...
            ],
            "speakers": ["SPEAKER_00", "SPEAKER_01", ...],
            "num_speakers": 2
        }
    """
    logger.info(f"Начинаю диаризацию: {audio_path}")

    pipeline = _get_diarization_pipeline()

    # Параметры диаризации
    params = {}
    if min_speakers is not None:
        params["min_speakers"] = min_speakers
    if max_speakers is not None:
        params["max_speakers"] = max_speakers

    logger.info(f"Параметры диаризации: {params if params else 'автоопределение'}")

    # Выполняем диаризацию
    diarization = pipeline(str(audio_path), **params)

    # Преобразуем результат в удобный формат
    segments = []
    speakers_set = set()

    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segment = {
            "start": float(turn.start),
            "end": float(turn.end),
            "speaker": speaker,
            "speaker_id": int(speaker.split("_")[-1])  # SPEAKER_00 -> 0
        }
        segments.append(segment)
        speakers_set.add(speaker)

    speakers = sorted(list(speakers_set))

    result = {
        "segments": segments,
        "speakers": speakers,
        "num_speakers": len(speakers)
    }

    logger.info(
        f"Диаризация завершена: найдено {result['num_speakers']} говорящих, "
        f"{len(segments)} сегментов"
    )

    return result


def merge_transcription_with_diarization(
    transcription: Dict[str, Any],
    diarization: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Объединяет результаты транскрипции Whisper с диаризацией.

    Для каждого сегмента транскрипции определяет, какой спикер говорил
    на основе временных меток диаризации.

    Args:
        transcription: Результат от Whisper (с segments)
        diarization: Результат диаризации (с segments и speakers)

    Returns:
        Обогащенная транскрипция с информацией о спикерах:
        {
            "text": "полный текст",
            "segments": [
                {
                    "start": 0.0,
                    "end": 2.5,
                    "text": "Здравствуйте",
                    "speaker": "SPEAKER_00",
                    "speaker_id": 0
                },
                ...
            ],
            "speakers": ["SPEAKER_00", "SPEAKER_01"],
            "num_speakers": 2
        }
    """
    logger.info("Объединяю транскрипцию с диаризацией")

    transcription_segments = transcription.get("segments", [])
    diarization_segments = diarization.get("segments", [])

    # Создаем новые сегменты с информацией о спикерах
    enriched_segments = []

    for trans_seg in transcription_segments:
        trans_start = trans_seg.get("start", 0.0)
        trans_end = trans_seg.get("end", 0.0)
        trans_mid = (trans_start + trans_end) / 2  # Середина сегмента

        # Находим спикера для этого временного отрезка
        # Берем спикера, сегмент которого покрывает середину транскрипционного сегмента
        assigned_speaker = None
        assigned_speaker_id = None

        for diar_seg in diarization_segments:
            if diar_seg["start"] <= trans_mid <= diar_seg["end"]:
                assigned_speaker = diar_seg["speaker"]
                assigned_speaker_id = diar_seg["speaker_id"]
                break

        # Если не нашли точного совпадения, берем ближайший
        if assigned_speaker is None:
            min_distance = float('inf')
            for diar_seg in diarization_segments:
                # Расстояние между серединами сегментов
                diar_mid = (diar_seg["start"] + diar_seg["end"]) / 2
                distance = abs(trans_mid - diar_mid)
                if distance < min_distance:
                    min_distance = distance
                    assigned_speaker = diar_seg["speaker"]
                    assigned_speaker_id = diar_seg["speaker_id"]

        # Добавляем обогащенный сегмент
        enriched_seg = {
            **trans_seg,  # Сохраняем все поля из транскрипции
            "speaker": assigned_speaker or "SPEAKER_UNKNOWN",
            "speaker_id": assigned_speaker_id if assigned_speaker_id is not None else -1
        }
        enriched_segments.append(enriched_seg)

    result = {
        "text": transcription.get("text", ""),
        "segments": enriched_segments,
        "speakers": diarization.get("speakers", []),
        "num_speakers": diarization.get("num_speakers", 0),
        "language": transcription.get("language"),
    }

    logger.info(
        f"Объединение завершено: {len(enriched_segments)} сегментов, "
        f"{result['num_speakers']} говорящих"
    )

    return result
