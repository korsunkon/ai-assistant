from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .config import ensure_data_dirs
from .db import engine, Base, SessionLocal
from .routes import calls, analysis, templates

# Настройка логирования
logger.add("logs/app.log", rotation="10 MB", retention="7 days", level="INFO")


def create_app() -> FastAPI:
    """
    Создаёт и настраивает экземпляр FastAPI-приложения.
    """
    logger.info("Инициализация приложения...")
    ensure_data_dirs()
    Base.metadata.create_all(bind=engine)
    logger.info("База данных инициализирована")

    app = FastAPI(title="AI Call Analytics MVP", version="0.1.0")

    # CORS — на время разработки открываем для localhost
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost", "http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(calls.router)
    app.include_router(analysis.router)
    app.include_router(templates.router)

    # Инициализация системных шаблонов
    db = SessionLocal()
    try:
        templates.init_system_templates(db)
        logger.info("Системные шаблоны инициализированы")
    finally:
        db.close()

    @app.get("/health")
    def healthcheck():
        return {"status": "ok"}

    return app


app = create_app()


