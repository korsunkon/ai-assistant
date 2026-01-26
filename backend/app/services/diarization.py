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

    Загрузка с HuggingFace с кэшированием - токен нужен только при первой загрузке.
    После этого модель кэшируется локально и токен не требуется.
    """
    global _diarization_pipeline

    if _diarization_pipeline is None:
        if not DIARIZATION_AVAILABLE:
            raise RuntimeError(
                "pyannote.audio не установлен. "
                "Установите: pip install pyannote.audio torch torchaudio"
            )

        import os

        # Получаем токен: сначала из settings (.env файл), потом из переменных окружения
        hf_token = settings.hf_token or os.environ.get('HF_TOKEN') or os.environ.get('HUGGINGFACE_TOKEN')

        model_name = settings.diarization_model
        # Если указан локальный путь, используем стандартное имя модели
        if model_name.startswith('./') or model_name.startswith('/') or '\\' in model_name:
            model_name = "pyannote/speaker-diarization-3.1"
            logger.info(f"Локальный путь не поддерживается в pyannote 3.1, используем HuggingFace: {model_name}")

        logger.info(f"Загружаю модель диаризации: {model_name}")

        try:
            # Загружаем с HuggingFace (модель кэшируется после первой загрузки)
            _diarization_pipeline = Pipeline.from_pretrained(
                model_name,
                use_auth_token=hf_token  # None если токен не установлен - попробует из кэша
            )

            # Переносим на GPU если доступен
            if torch.cuda.is_available():
                _diarization_pipeline.to(torch.device("cuda"))
                logger.info("Диаризация будет выполняться на GPU")
            else:
                logger.info("Диаризация будет выполняться на CPU")

        except Exception as e:
            logger.error(f"Ошибка загрузки модели диаризации: {e}")
            logger.info(
                "\n" + "="*60 + "\n"
                "ТРЕБУЕТСЯ HUGGINGFACE ТОКЕН ДЛЯ ДИАРИЗАЦИИ\n"
                "="*60 + "\n\n"
                "Для работы диаризации нужен токен HuggingFace (один раз для загрузки):\n\n"
                "1. Зарегистрируйтесь на https://huggingface.co\n"
                "2. Создайте токен: https://huggingface.co/settings/tokens\n"
                "3. Примите условия использования моделей:\n"
                "   - https://huggingface.co/pyannote/speaker-diarization-3.1\n"
                "   - https://huggingface.co/pyannote/segmentation-3.0\n"
                "4. Установите токен:\n"
                "   Windows: set HF_TOKEN=hf_ваш_токен\n"
                "   Linux/Mac: export HF_TOKEN=hf_ваш_токен\n\n"
                "После первой загрузки модели кэшируются и токен больше не нужен!\n"
                "="*60
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
