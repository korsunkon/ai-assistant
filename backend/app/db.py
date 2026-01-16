from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from .config import settings


class Base(DeclarativeBase):
    """
    Базовый класс для всех ORM-моделей.
    """


engine = create_engine(
    f"sqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Зависимость FastAPI для получения сессии БД.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


