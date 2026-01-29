from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Analysis, Call, AnalysisResult
from ..schemas import (
    AnalysisCreate,
    AnalysisCreateWithOptions,
    AnalysisRead,
    AnalysisStatus,
    AnalysisResultRead,
)
from ..services.pipeline import run_analysis_for_call

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("", response_model=List[AnalysisRead])
def list_analyses(
    db: Session = Depends(get_db),
):
    """
    Возвращает список всех исследований.
    """
    analyses = db.execute(select(Analysis).order_by(Analysis.created_at.desc())).scalars().all()
    return list(analyses)


@router.post("", response_model=AnalysisRead)
def create_analysis(
    payload: AnalysisCreateWithOptions,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Создаёт новое исследование и запускает фоновую обработку выбранных звонков.
    Поддерживает опцию force_retranscribe для принудительной ретранскрибации.
    """
    if not payload.call_ids:
        raise HTTPException(status_code=400, detail="Не выбрано ни одного звонка")

    calls = db.execute(select(Call).where(Call.id.in_(payload.call_ids))).scalars().all()
    if not calls:
        raise HTTPException(status_code=400, detail="Переданные звонки не найдены")

    analysis = Analysis(
        name=payload.name,
        query_text=payload.query_text,
        status="pending",
        progress=0,
        total_calls=len(calls),
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    # Запускаем фоновой таск
    background_tasks.add_task(
        _run_analysis_background, analysis.id, payload.call_ids, payload.query_text, payload.force_retranscribe
    )

    return analysis


def _run_analysis_background(analysis_id: int, call_ids: List[int], query_text: str, force_retranscribe: bool = False):
    """
    Фоновая функция, выполняющая полный анализ набора звонков.
    Вызывается через BackgroundTasks FastAPI.

    Args:
        force_retranscribe: Если True - принудительно транскрибировать все звонки заново
    """
    # #region agent log
    import json
    log_path = r"c:\Users\korsu\Documents\EnlighterProjects\project-036\.cursor\debug.log"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"analysis.py:68","message":"_run_analysis_background entry","data":{"analysis_id":analysis_id,"call_ids":call_ids,"query_text_length":len(query_text),"force_retranscribe":force_retranscribe},"timestamp":int(__import__("time").time()*1000)}) + "\n")
    # #endregion
    from ..db import SessionLocal  # локальный импорт, чтобы избежать циклов

    db = SessionLocal()
    try:
        analysis = db.get(Analysis, analysis_id)
        if not analysis:
            # #region agent log
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"analysis.py:77","message":"analysis not found","data":{"analysis_id":analysis_id},"timestamp":int(__import__("time").time()*1000)}) + "\n")
            # #endregion
            return

        calls = db.execute(select(Call).where(Call.id.in_(call_ids))).scalars().all()
        total = len(calls)
        processed = 0
        error_count = 0

        analysis.status = "running"
        db.commit()
        # #region agent log
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"analysis.py:87","message":"analysis started","data":{"total_calls":total,"call_ids":[c.id for c in calls]},"timestamp":int(__import__("time").time()*1000)}) + "\n")
        # #endregion

        for call in calls:
            try:
                # #region agent log
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"analysis.py:91","message":"processing call start","data":{"call_id":call.id,"call_filename":call.filename,"call_status_before":call.status},"timestamp":int(__import__("time").time()*1000)}) + "\n")
                # #endregion
                run_analysis_for_call(db, analysis, call, query_text, force_retranscribe)
                call.status = "processed"
                # #region agent log
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"analysis.py:95","message":"processing call success","data":{"call_id":call.id,"call_status_after":"processed"},"timestamp":int(__import__("time").time()*1000)}) + "\n")
                # #endregion
            except Exception as e:
                import traceback
                from loguru import logger
                logger.error(f"Ошибка обработки звонка {call.id} ({call.filename}): {str(e)}")
                logger.error(traceback.format_exc())
                call.status = "error"
                error_count += 1
                # #region agent log
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"analysis.py:102","message":"processing call error","data":{"call_id":call.id,"call_status_after":"error","error":str(e),"error_count":error_count},"timestamp":int(__import__("time").time()*1000)}) + "\n")
                # #endregion

            processed += 1
            analysis.progress = int(processed / total * 100)
            db.commit()
            # #region agent log
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"analysis.py:110","message":"progress update","data":{"processed":processed,"total":total,"progress":analysis.progress,"error_count":error_count},"timestamp":int(__import__("time").time()*1000)}) + "\n")
            # #endregion

        analysis.status = "completed" if error_count == 0 else "completed"  # даже с ошибками считаем завершённым
        db.commit()
        # #region agent log
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"analysis.py:115","message":"_run_analysis_background exit","data":{"final_status":analysis.status,"final_progress":analysis.progress,"final_error_count":error_count,"total_processed":processed},"timestamp":int(__import__("time").time()*1000)}) + "\n")
        # #endregion
    finally:
        db.close()


@router.get("/{analysis_id}", response_model=AnalysisStatus)
def get_analysis_status(
    analysis_id: int,
    db: Session = Depends(get_db),
):
    """
    Возвращает статус исследования и агрегированную статистику.
    """
    # #region agent log
    import json
    log_path = r"c:\Users\korsu\Documents\EnlighterProjects\project-036\.cursor\debug.log"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"analysis.py:111","message":"get_analysis_status entry","data":{"analysis_id":analysis_id},"timestamp":int(__import__("time").time()*1000)}) + "\n")
    # #endregion
    analysis = db.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Исследование не найдено")

    total_calls = analysis.total_calls or 0
    
    # Считаем количество успешно обработанных звонков (есть результаты)
    processed_count = (
        db.query(AnalysisResult.call_id)
        .filter(AnalysisResult.analysis_id == analysis.id)
        .distinct()
        .count()
    )
    # #region agent log
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"analysis.py:127","message":"processed_count calculated","data":{"processed_count":processed_count,"total_calls":total_calls},"timestamp":int(__import__("time").time()*1000)}) + "\n")
    # #endregion

    # Считаем ошибки: звонки, которые были в исследовании, но со статусом error
    error_count = (
        db.query(Call)
        .join(AnalysisResult, AnalysisResult.call_id == Call.id)
        .filter(
            AnalysisResult.analysis_id == analysis.id,
            Call.status == "error"
        )
        .distinct()
        .count()
    )
    # #region agent log
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"analysis.py:143","message":"error_count calculated (old logic)","data":{"error_count":error_count},"timestamp":int(__import__("time").time()*1000)}) + "\n")
    # #endregion
    
    # #region agent log
    # Check alternative error count: calls with status error that are part of this analysis
    from sqlalchemy import select
    result_call_ids = db.execute(select(AnalysisResult.call_id).where(AnalysisResult.analysis_id == analysis.id)).scalars().all()
    calls_in_analysis = db.execute(select(Call).where(Call.id.in_(result_call_ids))).scalars().all() if result_call_ids else []
    error_calls_alt = [c for c in calls_in_analysis if c.status == "error"]
    # Also check all calls with status error that might be part of analysis but don't have results
    all_error_calls = db.execute(select(Call).where(Call.status == "error")).scalars().all()
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"analysis.py:150","message":"alternative error count check","data":{"error_count_alt":len(error_calls_alt),"result_call_ids":list(result_call_ids),"all_call_statuses":[{"id":c.id,"status":c.status} for c in calls_in_analysis],"all_error_call_ids":[c.id for c in all_error_calls]},"timestamp":int(__import__("time").time()*1000)}) + "\n")
    # #endregion

    result = AnalysisStatus(
        id=analysis.id,
        status=analysis.status,
        progress=analysis.progress,
        total_calls=total_calls,
        processed_calls=processed_count,
        error_count=error_count,
    )
    # #region agent log
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"analysis.py:158","message":"get_analysis_status exit","data":{"result_status":result.status,"result_progress":result.progress,"result_total":result.total_calls,"result_processed":result.processed_calls,"result_errors":result.error_count},"timestamp":int(__import__("time").time()*1000)}) + "\n")
    # #endregion
    return result


@router.get("/{analysis_id}/results", response_model=List[AnalysisResultRead])
def get_analysis_results(
    analysis_id: int,
    db: Session = Depends(get_db),
):
    """
    Возвращает табличные результаты исследования по звонкам.
    """
    analysis = db.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Исследование не найдено")

    results = (
        db.query(AnalysisResult, Call)
        .join(Call, AnalysisResult.call_id == Call.id)
        .filter(AnalysisResult.analysis_id == analysis_id)
        .all()
    )

    out: List[AnalysisResultRead] = []
    for result, call in results:
        out.append(
            AnalysisResultRead(
                id=result.id,
                call_id=result.call_id,
                analysis_id=result.analysis_id,
                summary=result.summary,
                json_result=result.json_result,
                filename=call.filename,
            )
        )
    return out


@router.get("/{analysis_id}/dashboard")
def get_analysis_dashboard(
    analysis_id: int,
    db: Session = Depends(get_db),
):
    """
    Возвращает агрегированную статистику для Dashboard.
    Специально оптимизирован для анализа инцидентов (агрессия, конфликты).
    """
    import json as json_lib

    analysis = db.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Исследование не найдено")

    results = (
        db.query(AnalysisResult, Call)
        .join(Call, AnalysisResult.call_id == Call.id)
        .filter(AnalysisResult.analysis_id == analysis_id)
        .all()
    )

    total_files = len(results)
    files_with_incidents = 0
    total_incidents = 0
    incidents_by_type = {}
    severity_distribution = {"none": 0, "low": 0, "medium": 0, "high": 0}
    all_incidents = []

    for result, call in results:
        try:
            data = json_lib.loads(result.json_result or "{}")
        except:
            data = {}

        # Проверяем наличие инцидентов в разных форматах
        incidents = data.get("incidents", [])
        has_incidents = data.get("has_incidents", len(incidents) > 0)
        overall_severity = data.get("overall_severity", "none")

        if has_incidents and incidents:
            files_with_incidents += 1

        severity_distribution[overall_severity] = severity_distribution.get(overall_severity, 0) + 1

        for incident in incidents:
            total_incidents += 1
            inc_type = incident.get("type", "unknown")
            incidents_by_type[inc_type] = incidents_by_type.get(inc_type, 0) + 1

            all_incidents.append({
                "file_id": call.id,
                "filename": call.filename,
                "start_time": incident.get("start_time", 0),
                "end_time": incident.get("end_time", 0),
                "type": inc_type,
                "severity": incident.get("severity", "unknown"),
                "description": incident.get("description", ""),
                "quote": incident.get("quote", ""),
            })

    # Сортируем инциденты по severity (high -> medium -> low)
    severity_order = {"high": 0, "medium": 1, "low": 2, "unknown": 3}
    all_incidents.sort(key=lambda x: severity_order.get(x["severity"], 3))

    return {
        "analysis_id": analysis.id,
        "analysis_name": analysis.name,
        "stats": {
            "total_files": total_files,
            "files_with_incidents": files_with_incidents,
            "total_incidents": total_incidents,
            "incidents_by_type": incidents_by_type,
            "severity_distribution": severity_distribution,
        },
        "incidents": all_incidents,
    }


