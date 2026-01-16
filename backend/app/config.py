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

    # Whisper
    whisper_model_name: str = "large-v3"
    whisper_language: str | None = "ru"
    max_concurrent_transcriptions: int = 4

    # LLM (Ollama)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model_name: str = "qwen3:8b"

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


