"""
Миграция для добавления полей has_transcript и transcript_updated_at в таблицу calls.
Запускать один раз: python migrate_add_transcript_fields.py
"""
import sqlite3
from pathlib import Path

# Путь к БД (может быть в backend/data или в корне проекта/data)
db_path = Path(__file__).parent / "data" / "app.db"
if not db_path.exists():
    # Пробуем в корне проекта (project-036-enhanced/data)
    db_path = Path(__file__).parent.parent / "data" / "app.db"

if not db_path.exists():
    print(f"База данных не найдена")
    print(f"Проверенные пути:")
    print(f"  - {Path(__file__).parent / 'data' / 'app.db'}")
    print(f"  - {Path(__file__).parent.parent / 'data' / 'app.db'}")
    print("Создайте базу данных запустив приложение")
    exit(1)

print(f"Найдена БД: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Проверяем, есть ли уже колонки
cursor.execute("PRAGMA table_info(calls)")
columns = [col[1] for col in cursor.fetchall()]

migrations = []

if "has_transcript" not in columns:
    migrations.append(
        "ALTER TABLE calls ADD COLUMN has_transcript INTEGER DEFAULT 0 NOT NULL"
    )
    print("Добавляю колонку has_transcript...")

if "transcript_updated_at" not in columns:
    migrations.append(
        "ALTER TABLE calls ADD COLUMN transcript_updated_at DATETIME"
    )
    print("Добавляю колонку transcript_updated_at...")

if not migrations:
    print("Миграция не требуется - колонки уже существуют")
else:
    for sql in migrations:
        cursor.execute(sql)
    conn.commit()
    print("Миграция успешно выполнена!")

conn.close()
