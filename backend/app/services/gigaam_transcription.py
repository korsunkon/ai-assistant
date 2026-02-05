"""
Сервис транскрибации на базе GigaAM v3.

GigaAM - акустическая модель для русского языка от SberDevices.
Модель оптимизирована для русской речи и показывает лучшие результаты
чем Whisper на русском языке.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List

import torch
import torchaudio
from loguru import logger

_gigaam_model = None
_gigaam_available = None


def is_gigaam_available() -> bool:
    """Проверяет доступность библиотеки GigaAM."""
    global _gigaam_available
    if _gigaam_available is None:
        try:
            import gigaam
            _gigaam_available = True
            logger.info("GigaAM библиотека доступна")
        except ImportError:
            _gigaam_available = False
            logger.warning("GigaAM библиотека не установлена")
    return _gigaam_available


def _get_gigaam_model(model_name: str = "v3_e2e_rnnt"):
    """
    Ленивая загрузка модели GigaAM.

    Args:
        model_name: Имя модели. Доступные варианты:
            - v3_e2e_rnnt (рекомендуется) - лучшее качество с пунктуацией
            - v3_e2e_ctc - быстрее, но без пунктуации
            - v3_rnnt - без пунктуации
            - v2_rnnt - предыдущая версия
    """
    global _gigaam_model
    if _gigaam_model is None:
        import gigaam

        logger.info(f"Загрузка GigaAM модели '{model_name}'...")
        _gigaam_model = gigaam.load_model(model_name)
        logger.info(f"GigaAM модель '{model_name}' загружена")
    return _gigaam_model


def _prepare_audio_segment(
    audio_path: Path,
    start_sec: float,
    end_sec: float,
    target_sr: int = 16000
) -> Path:
    """
    Подготавливает сегмент аудио для транскрибации.

    GigaAM ожидает: mono, 16kHz, WAV.
    """
    waveform, sr = torchaudio.load(str(audio_path))

    # Конвертируем в моно если стерео
    if waveform.shape[0] > 1:
        waveform = torch.mean(waveform, dim=0, keepdim=True)

    # Вырезаем сегмент
    start_sample = int(sr * start_sec)
    end_sample = int(sr * end_sec)
    segment = waveform[:, start_sample:end_sample]

    # Ресэмплируем до 16kHz
    if sr != target_sr:
        resampler = torchaudio.transforms.Resample(sr, target_sr)
        segment = resampler(segment)

    # Сохраняем во временный файл
    temp_path = Path(tempfile.gettempdir()) / f"gigaam_segment_{start_sec}_{end_sec}.wav"
    torchaudio.save(str(temp_path), segment, target_sr)

    return temp_path


def _prepare_full_audio(audio_path: Path, target_sr: int = 16000) -> Path:
    """
    Подготавливает полный аудиофайл для транскрибации.
    """
    waveform, sr = torchaudio.load(str(audio_path))

    # Конвертируем в моно если стерео
    if waveform.shape[0] > 1:
        waveform = torch.mean(waveform, dim=0, keepdim=True)

    # Ресэмплируем до 16kHz
    if sr != target_sr:
        resampler = torchaudio.transforms.Resample(sr, target_sr)
        waveform = resampler(waveform)

    # Сохраняем во временный файл
    temp_path = Path(tempfile.gettempdir()) / f"gigaam_full_{audio_path.stem}.wav"
    torchaudio.save(str(temp_path), waveform, target_sr)

    return temp_path


def transcribe_segment(
    audio_path: Path,
    start_sec: float,
    end_sec: float,
    model_name: str = "v3_e2e_rnnt"
) -> str:
    """
    Транскрибирует один сегмент аудио.

    Args:
        audio_path: Путь к аудиофайлу
        start_sec: Начало сегмента (секунды)
        end_sec: Конец сегмента (секунды)
        model_name: Имя модели GigaAM

    Returns:
        Текст транскрипции
    """
    if not is_gigaam_available():
        raise RuntimeError("GigaAM не установлен")

    model = _get_gigaam_model(model_name)

    # Подготавливаем сегмент
    temp_path = _prepare_audio_segment(audio_path, start_sec, end_sec)

    try:
        # Транскрибируем
        text = model.transcribe(str(temp_path))
        return text.strip()
    finally:
        # Удаляем временный файл
        if temp_path.exists():
            temp_path.unlink()


def transcribe_with_segments(
    audio_path: Path,
    segments: List[Dict[str, Any]],
    model_name: str = "v3_e2e_rnnt"
) -> List[Dict[str, Any]]:
    """
    Транскрибирует аудио по заданным сегментам (например, от диаризации).

    Args:
        audio_path: Путь к аудиофайлу
        segments: Список сегментов с полями start, end, speaker
        model_name: Имя модели GigaAM

    Returns:
        Список сегментов с добавленным полем text
    """
    if not is_gigaam_available():
        raise RuntimeError("GigaAM не установлен")

    model = _get_gigaam_model(model_name)

    # Подготавливаем полное аудио один раз
    waveform, sr = torchaudio.load(str(audio_path))
    if waveform.shape[0] > 1:
        waveform = torch.mean(waveform, dim=0, keepdim=True)

    target_sr = 16000
    if sr != target_sr:
        resampler = torchaudio.transforms.Resample(sr, target_sr)
        waveform = resampler(waveform)

    result_segments = []

    for seg in segments:
        start_sec = seg.get("start", 0)
        end_sec = seg.get("end", 0)

        # Вырезаем сегмент
        start_sample = int(target_sr * start_sec)
        end_sample = int(target_sr * end_sec)
        segment_audio = waveform[:, start_sample:end_sample]

        # Сохраняем во временный файл
        temp_path = Path(tempfile.gettempdir()) / f"gigaam_seg_{start_sec:.2f}_{end_sec:.2f}.wav"
        torchaudio.save(str(temp_path), segment_audio, target_sr)

        try:
            # Транскрибируем
            text = model.transcribe(str(temp_path))

            result_segments.append({
                **seg,
                "text": text.strip()
            })
        except Exception as e:
            logger.warning(f"Ошибка транскрибации сегмента [{start_sec:.1f}-{end_sec:.1f}]: {e}")
            result_segments.append({
                **seg,
                "text": ""
            })
        finally:
            if temp_path.exists():
                temp_path.unlink()

    return result_segments


def transcribe_full(
    audio_path: Path,
    model_name: str = "v3_e2e_rnnt",
    chunk_duration: float = 20.0
) -> Dict[str, Any]:
    """
    Транскрибирует полный аудиофайл, разбивая на чанки.

    GigaAM работает лучше с короткими сегментами (до 25 сек).
    Для длинных файлов разбиваем на чанки.

    Args:
        audio_path: Путь к аудиофайлу
        model_name: Имя модели GigaAM
        chunk_duration: Длительность чанка в секундах

    Returns:
        Словарь с результатом транскрипции (формат совместим с Whisper)
    """
    if not is_gigaam_available():
        raise RuntimeError("GigaAM не установлен")

    model = _get_gigaam_model(model_name)

    # Загружаем аудио
    waveform, sr = torchaudio.load(str(audio_path))
    duration = waveform.shape[1] / sr

    logger.info(f"GigaAM: транскрибация {audio_path.name}, длительность {duration:.1f}s")

    # Конвертируем в моно
    if waveform.shape[0] > 1:
        waveform = torch.mean(waveform, dim=0, keepdim=True)

    # Ресэмплируем до 16kHz
    target_sr = 16000
    if sr != target_sr:
        resampler = torchaudio.transforms.Resample(sr, target_sr)
        waveform = resampler(waveform)
        duration = waveform.shape[1] / target_sr

    segments = []
    full_text_parts = []

    # Разбиваем на чанки
    current_pos = 0.0
    segment_id = 0

    while current_pos < duration:
        chunk_end = min(current_pos + chunk_duration, duration)

        # Вырезаем чанк
        start_sample = int(target_sr * current_pos)
        end_sample = int(target_sr * chunk_end)
        chunk_audio = waveform[:, start_sample:end_sample]

        # Сохраняем во временный файл
        temp_path = Path(tempfile.gettempdir()) / f"gigaam_chunk_{segment_id}.wav"
        torchaudio.save(str(temp_path), chunk_audio, target_sr)

        try:
            # Транскрибируем чанк
            text = model.transcribe(str(temp_path))
            text = text.strip()

            if text:
                segments.append({
                    "id": segment_id,
                    "start": current_pos,
                    "end": chunk_end,
                    "text": text,
                })
                full_text_parts.append(text)

        except Exception as e:
            logger.warning(f"Ошибка транскрибации чанка [{current_pos:.1f}-{chunk_end:.1f}]: {e}")
        finally:
            if temp_path.exists():
                temp_path.unlink()

        segment_id += 1
        current_pos = chunk_end

    return {
        "text": " ".join(full_text_parts),
        "segments": segments,
        "language": "ru",
        "duration": duration
    }


def cleanup_gigaam_model():
    """Освобождает память от модели GigaAM."""
    global _gigaam_model
    if _gigaam_model is not None:
        del _gigaam_model
        _gigaam_model = None
        torch.cuda.empty_cache() if torch.cuda.is_available() else None
        logger.info("GigaAM модель выгружена из памяти")
