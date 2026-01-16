from __future__ import annotations

import json
from typing import Any, Dict

import httpx
from loguru import logger

from ..config import settings


class OllamaClient:
    """
    Простой клиент для обращения к локальному Ollama API.
    """

    def __init__(self, base_url: str | None = None, model_name: str | None = None):
        self.base_url = base_url or settings.ollama_base_url
        self.model_name = model_name or settings.ollama_model_name

    def generate(self, prompt: str, json_mode: bool = False) -> str:
        """
        Синхронный вызов модели Qwen через Ollama.
        """
        url = f"{self.base_url}/api/chat"
        headers = {"Content-Type": "application/json"}

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "stream": False,
        }

        if json_mode:
            # Ollama понимает этот флаг и старается вернуть корректный JSON
            payload["format"] = "json"

        logger.debug(f"Отправляю запрос к Ollama: {self.base_url}, модель: {self.model_name}")
        
        try:
            with httpx.Client(timeout=120.0) as client:
                resp = client.post(url, headers=headers, content=json.dumps(payload))
                resp.raise_for_status()
                data = resp.json()
        except httpx.ConnectError as e:
            logger.error(f"Не удалось подключиться к Ollama по адресу {self.base_url}: {str(e)}")
            raise RuntimeError(f"Ollama недоступен. Убедитесь, что Ollama запущен и доступен по адресу {self.base_url}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Ошибка HTTP от Ollama: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Неожиданная ошибка при обращении к Ollama: {str(e)}")
            raise

        # Формат ответа Ollama: { "message": { "content": "..." }, ... }
        message = data.get("message") or {}
        content = message.get("content") or ""
        
        if not content:
            logger.warning(f"Пустой ответ от Ollama. Полный ответ: {data}")
        
        return content


