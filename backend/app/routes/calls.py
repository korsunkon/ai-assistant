from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings, ensure_data_dirs
from ..db import get_db
from ..models import Call
from ..schemas import CallRead

router = APIRouter(prefix="/calls", tags=["calls"])


@router.post("/upload", response_model=List[CallRead])
async def upload_calls(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """
    Загрузка одного или нескольких аудиофайлов звонков.
    Файлы сохраняются в data/audio, в БД создаются записи о звонках.
    """
    ensure_data_dirs()
    audio_dir = settings.data_root / settings.audio_dir_name

    results: List[Call] = []

    for file in files:
        if not file.filename:
            continue

        suffix = Path(file.filename).suffix.lower()
        if suffix not in {".mp3", ".wav"}:
            raise HTTPException(
                status_code=400,
                detail=f"Неподдерживаемый формат файла: {file.filename}",
            )

        dest_path = audio_dir / file.filename

        # Если файл с таким именем уже есть — добавим метку времени
        if dest_path.exists():
            stem = dest_path.stem
            dest_path = audio_dir / f"{stem}_{int(datetime.utcnow().timestamp())}{suffix}"

        content = await file.read()
        dest_path.write_bytes(content)

        size_bytes = len(content)

        call = Call(
            filename=dest_path.name,
            original_path=str(dest_path.absolute()),  # Сохраняем абсолютный путь
            duration_sec=None,
            size_bytes=size_bytes,
            status="new",
        )
        db.add(call)
        db.flush()  # чтобы получить id без коммита
        results.append(call)

    db.commit()

    return results


@router.get("", response_model=List[CallRead])
def list_calls(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """
    Список звонков с базовыми фильтрами по статусу и названию файла.
    """
    stmt = select(Call)
    if status:
        stmt = stmt.where(Call.status == status)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(Call.filename.like(pattern))

    calls = db.execute(stmt).scalars().all()
    return calls


@router.get("/{call_id}/transcript")
def get_call_transcript(
    call_id: int,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Получение транскрипта звонка в JSON формате.
    Возвращает полный транскрипт со всеми сегментами и временными метками.
    """
    call = db.get(Call, call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Звонок не найден")

    # Проверяем, что звонок был обработан
    if call.status not in ["processed", "processing"]:
        raise HTTPException(
            status_code=400,
            detail=f"Транскрипт недоступен. Статус звонка: {call.status}"
        )

    # Ищем файл транскрипта
    transcripts_dir = settings.data_root / settings.transcripts_dir_name
    transcript_path = transcripts_dir / f"{call_id}.json"

    if not transcript_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Файл транскрипта не найден"
        )

    try:
        transcript_data = json.loads(transcript_path.read_text(encoding="utf-8"))
        return transcript_data
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка чтения транскрипта: {str(e)}"
        )


@router.delete("/{call_id}")
def delete_call(
    call_id: int,
    db: Session = Depends(get_db),
):
    """
    Удаляет звонок и привязанные к нему результаты анализа.
    """
    call = db.get(Call, call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Звонок не найден")

    # Пытаемся удалить файл с диска (ошибка не критична)
    try:
        path = Path(call.original_path)
        if path.exists():
            path.unlink()
    except Exception:
        pass

    db.delete(call)
    db.commit()

    return {"status": "ok"}


