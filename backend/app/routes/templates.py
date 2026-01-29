from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AnalysisTemplate
from ..schemas import AnalysisTemplateRead, AnalysisTemplateCreate

router = APIRouter(prefix="/templates", tags=["templates"])

# Предустановленные системные шаблоны
SYSTEM_TEMPLATES = [
    {
        "name": "Анализ агрессии",
        "description": "Детектирование вербальной агрессии и конфликтных ситуаций с точными тайм-кодами",
        "category": "security",
        "query_text": """Проанализируй аудиозапись на наличие признаков агрессии и конфликтов.

Ищи следующие типы инцидентов:
1. ВЕРБАЛЬНАЯ АГРЕССИЯ: крики, оскорбления, угрозы, ненормативная лексика, повышенный тон
2. КОНФЛИКТ: споры, взаимные претензии, эскалация напряжённости
3. ЗВУКИ ФИЗИЧЕСКОЙ АГРЕССИИ: удары, падения, крики боли, звуки борьбы

Для КАЖДОГО инцидента укажи:
- Точное время начала и конца (в секундах)
- Тип инцидента
- Уровень серьёзности (low/medium/high)
- Краткое описание что происходит
- Цитату из транскрипта (если есть речь)

Ответь строго в JSON формате:
{
  "summary": "общее описание ситуации в записи",
  "has_incidents": true/false,
  "total_incidents": число,
  "incidents": [
    {
      "start_time": число (секунды),
      "end_time": число (секунды),
      "type": "verbal_aggression" | "conflict" | "physical",
      "severity": "low" | "medium" | "high",
      "description": "что происходит",
      "quote": "цитата если есть"
    }
  ],
  "overall_severity": "none" | "low" | "medium" | "high"
}"""
    },
    {
        "name": "Анализ качества обслуживания",
        "description": "Оценка работы сотрудника: приветствие, выявление потребностей, работа с возражениями",
        "category": "quality",
        "query_text": """Оцени качество обслуживания клиента по следующим критериям:

1. Приветствие и представление (было ли, насколько корректно)
2. Выявление потребностей клиента
3. Презентация решения/продукта
4. Работа с возражениями
5. Завершение разговора

Для каждого критерия укажи:
- Оценку (1-5)
- Комментарий
- Цитату из разговора

Ответь в JSON:
{
  "summary": "общая оценка звонка",
  "overall_score": число от 1 до 5,
  "findings": [
    {"criterion": "название критерия", "score": число, "comment": "комментарий", "evidence": ["цитаты"]}
  ]
}"""
    },
    {
        "name": "Причины отказов",
        "description": "Анализ причин отказа от покупки или услуги",
        "category": "sales",
        "query_text": """Проанализируй звонок и определи:

1. Была ли совершена покупка/сделка? (Да/Нет)
2. Если нет - какая конкретная причина отказа?
3. Упоминались ли конкуренты? Какие?
4. Какие возражения озвучивал клиент?
5. Была ли попытка удержать клиента?

Ответь в JSON:
{
  "summary": "краткое описание итога звонка",
  "purchase_made": true/false,
  "rejection_reason": "причина отказа или null",
  "competitors_mentioned": ["список конкурентов"],
  "objections": ["список возражений"],
  "retention_attempted": true/false,
  "findings": [
    {"criterion": "...", "value": "...", "evidence": ["цитаты"]}
  ]
}"""
    }
]


def init_system_templates(db: Session) -> None:
    """Инициализирует системные шаблоны при первом запуске"""
    for template_data in SYSTEM_TEMPLATES:
        existing = db.execute(
            select(AnalysisTemplate).where(
                AnalysisTemplate.name == template_data["name"],
                AnalysisTemplate.is_system == True
            )
        ).scalar_one_or_none()

        if not existing:
            template = AnalysisTemplate(
                name=template_data["name"],
                description=template_data["description"],
                query_text=template_data["query_text"],
                category=template_data["category"],
                is_system=True
            )
            db.add(template)

    db.commit()


@router.get("", response_model=List[AnalysisTemplateRead])
def list_templates(
    db: Session = Depends(get_db),
    category: str = None,
):
    """Получить список всех шаблонов анализа"""
    stmt = select(AnalysisTemplate)
    if category:
        stmt = stmt.where(AnalysisTemplate.category == category)

    templates = db.execute(stmt).scalars().all()
    return templates


@router.get("/{template_id}", response_model=AnalysisTemplateRead)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
):
    """Получить шаблон по ID"""
    template = db.get(AnalysisTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Шаблон не найден")
    return template


@router.post("", response_model=AnalysisTemplateRead)
def create_template(
    data: AnalysisTemplateCreate,
    db: Session = Depends(get_db),
):
    """Создать новый пользовательский шаблон"""
    template = AnalysisTemplate(
        name=data.name,
        description=data.description,
        query_text=data.query_text,
        category=data.category,
        is_system=False
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.delete("/{template_id}")
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
):
    """Удалить пользовательский шаблон (системные нельзя удалять)"""
    template = db.get(AnalysisTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Шаблон не найден")

    if template.is_system:
        raise HTTPException(status_code=403, detail="Системные шаблоны нельзя удалять")

    db.delete(template)
    db.commit()
    return {"status": "ok"}
