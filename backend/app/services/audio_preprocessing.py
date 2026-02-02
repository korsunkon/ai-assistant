"""
Модуль предобработки аудио для улучшения качества транскрибации.

Использует FFmpeg для:
1. Нормализации громкости (loudnorm)
2. Компрессии динамического диапазона
3. Шумоподавления (afftdn)
4. Highpass фильтр для удаления низкочастотного гула
"""
from __future__ import annotations

import subprocess
import shutil
from pathlib import Path
from typing import Optional

from loguru import logger

from ..config import settings


# Путь к FFmpeg (определяется при загрузке модуля)
FFMPEG_PATH: Optional[str] = None


def _find_ffmpeg() -> Optional[str]:
    """
    Находит путь к ffmpeg.exe
    """
    # Сначала проверяем в PATH
    ffmpeg_in_path = shutil.which("ffmpeg")
    if ffmpeg_in_path:
        return ffmpeg_in_path

    # Проверяем стандартные пути установки winget
    winget_paths = [
        Path.home() / "AppData/Local/Microsoft/WinGet/Packages",
    ]

    for base_path in winget_paths:
        if base_path.exists():
            # Ищем ffmpeg.exe рекурсивно
            for ffmpeg_exe in base_path.rglob("ffmpeg.exe"):
                return str(ffmpeg_exe)

    # Проверяем другие стандартные пути
    standard_paths = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
    ]

    for path in standard_paths:
        if Path(path).exists():
            return path

    return None


def _init_ffmpeg():
    """
    Инициализирует путь к FFmpeg при первом использовании.
    """
    global FFMPEG_PATH
    if FFMPEG_PATH is None:
        FFMPEG_PATH = _find_ffmpeg()
        if FFMPEG_PATH:
            logger.info(f"FFmpeg найден: {FFMPEG_PATH}")
        else:
            logger.warning("FFmpeg не найден. Предобработка аудио будет отключена.")


def is_ffmpeg_available() -> bool:
    """
    Проверяет, доступен ли FFmpeg.
    """
    _init_ffmpeg()
    return FFMPEG_PATH is not None


def preprocess_audio(
    input_path: Path,
    output_path: Optional[Path] = None,
    normalize: bool = True,
    compress: bool = True,
    denoise: bool = True,
    highpass: bool = True,
    highpass_freq: int = 80,
) -> Path:
    """
    Предобрабатывает аудиофайл для улучшения качества транскрибации.

    Args:
        input_path: Путь к исходному аудиофайлу
        output_path: Путь для сохранения результата (если None - создаётся временный файл)
        normalize: Нормализация громкости (EBU R128 loudnorm)
        compress: Компрессия динамического диапазона
        denoise: Шумоподавление (afftdn)
        highpass: Highpass фильтр для удаления низкочастотного гула
        highpass_freq: Частота среза highpass фильтра (Hz)

    Returns:
        Путь к обработанному файлу

    Raises:
        RuntimeError: Если FFmpeg не найден или обработка не удалась
    """
    _init_ffmpeg()

    if not FFMPEG_PATH:
        raise RuntimeError("FFmpeg не найден. Установите FFmpeg для предобработки аудио.")

    if not input_path.exists():
        raise FileNotFoundError(f"Исходный файл не найден: {input_path}")

    # Определяем выходной путь
    if output_path is None:
        cache_dir = settings.data_root / settings.cache_dir_name / "preprocessed"
        cache_dir.mkdir(parents=True, exist_ok=True)
        output_path = cache_dir / f"{input_path.stem}_processed.wav"

    # Строим цепочку аудио-фильтров
    filters = []

    # 1. Highpass фильтр - удаляет низкочастотный гул (кондиционеры, вентиляция)
    if highpass:
        filters.append(f"highpass=f={highpass_freq}")

    # 2. Шумоподавление - afftdn (адаптивный FFT denoiser)
    # nr: noise reduction (0-97), nf: noise floor (dB)
    if denoise:
        filters.append("afftdn=nf=-25:nr=10:tn=1")

    # 3. Компрессия динамического диапазона - поднимает тихие звуки
    if compress:
        # attack: время атаки (сек), release: время отпускания
        # threshold: порог срабатывания (дБ), ratio: степень компрессии
        # makeup: компенсация громкости после компрессии
        filters.append(
            "acompressor=threshold=-20dB:ratio=4:attack=5:release=50:makeup=8dB"
        )

    # 4. Нормализация громкости по стандарту EBU R128
    if normalize:
        # I: целевая интегральная громкость (-24 LUFS стандарт, -16 для речи громче)
        # TP: True Peak максимум
        # LRA: целевой диапазон громкости
        filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")

    # Собираем команду FFmpeg
    filter_chain = ",".join(filters) if filters else "anull"

    cmd = [
        FFMPEG_PATH,
        "-y",  # Перезаписывать без вопросов
        "-i", str(input_path),
        "-af", filter_chain,
        "-ar", "16000",  # 16kHz - оптимально для Whisper
        "-ac", "1",  # Моно
        "-c:a", "pcm_s16le",  # 16-bit PCM WAV
        str(output_path),
    ]

    logger.info(f"Предобработка аудио: {input_path.name}")
    logger.debug(f"FFmpeg команда: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 минут максимум
        )

        if result.returncode != 0:
            logger.error(f"FFmpeg ошибка: {result.stderr}")
            raise RuntimeError(f"FFmpeg вернул код {result.returncode}: {result.stderr}")

        logger.info(f"Аудио обработано: {output_path.name}")
        return output_path

    except subprocess.TimeoutExpired:
        logger.error(f"Таймаут при обработке {input_path.name}")
        raise RuntimeError("Превышено время обработки аудио")
    except Exception as e:
        logger.error(f"Ошибка при обработке {input_path.name}: {e}")
        raise


def cleanup_preprocessed_file(file_path: Path) -> None:
    """
    Удаляет временный обработанный файл.
    """
    try:
        if file_path.exists():
            file_path.unlink()
            logger.debug(f"Удалён временный файл: {file_path}")
    except Exception as e:
        logger.warning(f"Не удалось удалить временный файл {file_path}: {e}")
