from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Глобальные настройки backend-приложения.

    Вынесены в класс, чтобы при необходимости их можно было
    переопределять через переменные окружения.
    """

    # Корень данных
    data_root: Path = Path("data")

    # Подкаталоги
    audio_dir_name: str = "audio"
    transcripts_dir_name: str = "transcripts"
    results_dir_name: str = "results"
    cache_dir_name: str = "cache"

    # Файл базы данных SQLite
    db_path: Path = Path("data") / "app.db"

    # Транскрибация
    # Выбор движка: "whisper" или "gigaam"
    transcription_engine: str = "gigaam"  # gigaam рекомендуется для русского языка

    # Whisper настройки
    whisper_model_name: str = "large-v3"
    whisper_language: str | None = "ru"
    max_concurrent_transcriptions: int = 2  # Оптимально для RTX 4090 Laptop (16GB VRAM)

    # GigaAM настройки (для русского языка)
    # Доступные модели: v3_e2e_rnnt (рекомендуется), v3_e2e_ctc, v3_rnnt, v2_rnnt
    gigaam_model_name: str = "v3_e2e_rnnt"
    gigaam_chunk_duration: float = 20.0  # Длительность чанка для разбиения длинных файлов

    # Диаризация (pyannote.audio)
    # Модель загружается с HuggingFace и кэшируется локально.
    # При первом запуске требуется HF_TOKEN (установите в .env файле)
    # После загрузки модель кэшируется и токен больше не нужен.
    diarization_model: str = "pyannote/speaker-diarization-3.1"
    diarization_enabled: bool = True
    min_speakers: int | None = None  # None = автоопределение
    max_speakers: int | None = None  # None = автоопределение
    hf_token: str | None = None  # HuggingFace токен для загрузки моделей

    # LLM (Ollama)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model_name: str = "qwen3:8b"
    role_assignment_enabled: bool = True  # Определять роли через Qwen

    # Предобработка аудио (FFmpeg)
    audio_preprocessing_enabled: bool = True  # Включить предобработку аудио
    audio_normalize: bool = True  # Нормализация громкости (EBU R128)
    audio_compress: bool = True  # Компрессия динамического диапазона
    audio_denoise: bool = True  # Шумоподавление
    audio_highpass: bool = True  # Highpass фильтр (удаление низких частот)
    audio_highpass_freq: int = 80  # Частота среза highpass (Hz)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


def ensure_data_dirs() -> None:
    """
    Создаёт директории для данных, если их ещё нет.
    """
    root = settings.data_root
    (root / settings.audio_dir_name).mkdir(parents=True, exist_ok=True)
    (root / settings.transcripts_dir_name).mkdir(parents=True, exist_ok=True)
    (root / settings.results_dir_name).mkdir(parents=True, exist_ok=True)
    (root / settings.cache_dir_name).mkdir(parents=True, exist_ok=True)


