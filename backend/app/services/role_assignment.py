"""
Модуль для автоматического определения ролей говорящих с помощью LLM (Qwen)
"""
from __future__ import annotations

import json
from typing import Dict, Any, List
from loguru import logger

from .ollama_client import OllamaClient


def assign_roles_with_llm(
    transcript_with_speakers: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Определяет роли говорящих (Клиент, Сотрудник, etc.) используя Qwen.

    Анализирует содержание реплик каждого спикера и определяет его роль
    на основе контекста разговора.

    Args:
        transcript_with_speakers: Транскрипт с определенными спикерами
            {
                "segments": [{"speaker": "SPEAKER_00", "text": "...", ...}],
                "speakers": ["SPEAKER_00", "SPEAKER_01"],
                "num_speakers": 2
            }

    Returns:
        Транскрипт с назначенными ролями:
        {
            "segments": [{"speaker": "SPEAKER_00", "role": "Сотрудник", "text": "...", ...}],
            "speaker_roles": {"SPEAKER_00": "Сотрудник", "SPEAKER_01": "Клиент"},
            ...
        }
    """
    logger.info("Начинаю определение ролей через LLM")

    speakers = transcript_with_speakers.get("speakers", [])
    segments = transcript_with_speakers.get("segments", [])

    if not speakers:
        logger.warning("Нет информации о спикерах, роли не определены")
        return transcript_with_speakers

    # Группируем реплики по спикерам для анализа
    speaker_texts = {speaker: [] for speaker in speakers}
    for seg in segments:
        speaker = seg.get("speaker")
        text = seg.get("text", "").strip()
        if speaker and text:
            speaker_texts[speaker].append(text)

    # Формируем prompt для LLM
    speaker_samples = {}
    for speaker, texts in speaker_texts.items():
        # Берем первые 5-10 реплик для анализа
        sample = " ".join(texts[:10])
        speaker_samples[speaker] = sample

    prompt = _build_role_assignment_prompt(speaker_samples)

    # Запрашиваем LLM
    client = OllamaClient()

    try:
        raw_response = client.generate(prompt, json_mode=True)
        logger.info("Получен ответ от LLM по определению ролей")
    except Exception as e:
        logger.error(f"Ошибка при обращении к LLM для определения ролей: {e}")
        # Fallback: простое присвоение ролей
        return _assign_roles_fallback(transcript_with_speakers)

    # Парсим ответ
    try:
        role_mapping = json.loads(raw_response)
        speaker_roles = role_mapping.get("speaker_roles", {})
        reasoning = role_mapping.get("reasoning", "")

        logger.info(f"LLM определил роли: {speaker_roles}")
        if reasoning:
            logger.debug(f"Обоснование: {reasoning}")

    except Exception as e:
        logger.warning(f"Ошибка парсинга ответа LLM: {e}")
        return _assign_roles_fallback(transcript_with_speakers)

    # Применяем роли к сегментам
    enriched_segments = []
    for seg in segments:
        speaker = seg.get("speaker")
        role = speaker_roles.get(speaker, "Неизвестный")

        enriched_seg = {
            **seg,
            "role": role
        }
        enriched_segments.append(enriched_seg)

    result = {
        **transcript_with_speakers,
        "segments": enriched_segments,
        "speaker_roles": speaker_roles
    }

    logger.info(f"Роли присвоены: {speaker_roles}")
    return result


def _build_role_assignment_prompt(speaker_samples: Dict[str, str]) -> str:
    """
    Формирует prompt для LLM по определению ролей.
    """
    speakers_info = []
    for speaker, sample_text in speaker_samples.items():
        speakers_info.append(f"{speaker}: \"{sample_text[:300]}...\"")

    speakers_list = "\n".join(speakers_info)

    prompt = f"""Ты аналитик звонков в контакт-центре. Тебе нужно определить роли говорящих в записи звонка.

Доступные роли:
- Сотрудник (менеджер, оператор call-центра)
- Клиент (звонящий, покупатель)
- Менеджер/Руководитель (если есть)
- Другое (если роль непонятна)

Образцы реплик каждого говорящего:

{speakers_list}

Проанализируй содержание реплик и определи роль каждого говорящего.

Признаки СОТРУДНИКА:
- Приветствие от имени компании ("Здравствуйте, компания X")
- Предложение помощи ("Чем могу помочь?")
- Профессиональная лексика
- Ответы на вопросы
- Уточняющие вопросы для оформления заказа

Признаки КЛИЕНТА:
- Задает вопросы ("Сколько стоит?", "Есть ли в наличии?")
- Высказывает потребности ("Хочу заказать", "Мне нужно")
- Может использовать разговорную речь

Ответь СТРОГО в формате JSON:
{{
  "speaker_roles": {{
    "SPEAKER_00": "Сотрудник",
    "SPEAKER_01": "Клиент"
  }},
  "reasoning": "Краткое объяснение почему определены именно эти роли"
}}"""

    return prompt


def _assign_roles_fallback(transcript_with_speakers: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fallback: простое эвристическое присвоение ролей.

    Первый говорящий = Сотрудник (обычно начинает разговор)
    Второй = Клиент
    Остальные = по порядку чередования
    """
    logger.info("Используем fallback для определения ролей")

    speakers = transcript_with_speakers.get("speakers", [])
    segments = transcript_with_speakers.get("segments", [])

    # Простая эвристика
    speaker_roles = {}
    default_roles = ["Сотрудник", "Клиент", "Собеседник 3", "Собеседник 4"]

    for idx, speaker in enumerate(speakers):
        if idx < len(default_roles):
            speaker_roles[speaker] = default_roles[idx]
        else:
            speaker_roles[speaker] = f"Собеседник {idx + 1}"

    # Применяем к сегментам
    enriched_segments = []
    for seg in segments:
        speaker = seg.get("speaker")
        role = speaker_roles.get(speaker, "Неизвестный")

        enriched_seg = {
            **seg,
            "role": role
        }
        enriched_segments.append(enriched_seg)

    result = {
        **transcript_with_speakers,
        "segments": enriched_segments,
        "speaker_roles": speaker_roles
    }

    logger.info(f"Роли присвоены (fallback): {speaker_roles}")
    return result
