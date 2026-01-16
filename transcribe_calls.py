import os
import openai
import pandas as pd
from pathlib import Path
import json
from typing import List, Dict, Any
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CallTranscriber:
    def __init__(self, api_key: str):
        """Инициализация транскрибера с API ключом OpenAI"""
        self.client = openai.OpenAI(api_key=api_key)
        
    def transcribe_audio(self, audio_file_path: str) -> Dict[str, Any]:
        """
        Транскрибирует аудио файл с помощью Whisper API
        """
        try:
            logger.info(f"Транскрибирую файл: {audio_file_path}")
            
            with open(audio_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["word"]
                )
            
            logger.info(f"Транскрибация завершена для: {audio_file_path}")
            return transcript
            
        except Exception as e:
            logger.error(f"Ошибка при транскрибации {audio_file_path}: {str(e)}")
            return None
    
    def process_transcript(self, transcript: Dict[str, Any], manager_name: str) -> List[Dict[str, str]]:
        """
        Обрабатывает транскрипт и извлекает реплики с ролями
        """
        conversations = []
        
        if not transcript or 'segments' not in transcript:
            logger.warning(f"Нет сегментов в транскрипте для {manager_name}")
            return conversations
        
        for segment in transcript['segments']:
            if 'words' in segment and segment['words']:
                # Группируем слова в реплики по временным интервалам
                text = segment['text'].strip()
                if text:
                    # Определяем роль на основе контекста (можно настроить)
                    role = self._determine_role(text, manager_name)
                    
                    conversations.append({
                        'manager_name': manager_name,
                        'role': role,
                        'replica': text
                    })
        
        return conversations
    
    def _determine_role(self, text: str, manager_name: str) -> str:
        """
        Определяет роль говорящего на основе текста
        Можно настроить логику определения ролей
        """
        text_lower = text.lower()
        
        # Простая логика определения ролей (можно улучшить)
        if any(word in text_lower for word in ['здравствуйте', 'добрый день', 'спасибо', 'до свидания']):
            return 'Менеджер'
        elif any(word in text_lower for word in ['да', 'нет', 'хорошо', 'понятно']):
            return 'Клиент'
        else:
            return 'Неопределено'
    
    def process_directory(self, audio_dir: str) -> List[Dict[str, str]]:
        """
        Обрабатывает все MP3 файлы в директории
        """
        all_conversations = []
        audio_path = Path(audio_dir)
        
        # Находим все MP3 файлы
        mp3_files = list(audio_path.glob("*.mp3"))
        
        if not mp3_files:
            logger.warning(f"MP3 файлы не найдены в директории: {audio_dir}")
            return all_conversations
        
        logger.info(f"Найдено {len(mp3_files)} MP3 файлов")
        
        for mp3_file in mp3_files:
            manager_name = mp3_file.stem  # Имя файла без расширения
            
            # Транскрибируем файл
            transcript = self.transcribe_audio(str(mp3_file))
            
            if transcript:
                # Обрабатываем транскрипт
                conversations = self.process_transcript(transcript, manager_name)
                all_conversations.extend(conversations)
                
                logger.info(f"Обработан файл {manager_name}: {len(conversations)} реплик")
            else:
                logger.error(f"Не удалось транскрибировать файл: {mp3_file}")
        
        return all_conversations
    
    def export_to_excel(self, conversations: List[Dict[str, str]], output_file: str = "transcribed_calls.xlsx"):
        """
        Экспортирует результаты в Excel файл
        """
        if not conversations:
            logger.warning("Нет данных для экспорта")
            return
        
        # Создаем DataFrame
        df = pd.DataFrame(conversations)
        
        # Сохраняем в Excel
        df.to_excel(output_file, index=False, sheet_name='Транскрибированные звонки')
        
        logger.info(f"Результаты экспортированы в {output_file}")
        logger.info(f"Всего реплик: {len(conversations)}")
        
        # Показываем статистику
        print(f"\nСтатистика транскрибации:")
        print(f"Всего реплик: {len(conversations)}")
        print(f"Менеджеров: {df['manager_name'].nunique()}")
        print(f"Ролей: {df['role'].value_counts().to_dict()}")


def main():
    """
    Основная функция для запуска транскрибации
    """
    # Получаем API ключ из переменной окружения
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        logger.error("Не установлена переменная окружения OPENAI_API_KEY")
        print("Пожалуйста, установите переменную окружения OPENAI_API_KEY")
        return
    
    # Создаем транскрибер
    transcriber = CallTranscriber(api_key)
    
    # Директория с MP3 файлами
    audio_directory = "calls"  # Можно изменить на нужную директорию
    
    if not os.path.exists(audio_directory):
        logger.error(f"Директория {audio_directory} не существует")
        print(f"Создайте директорию {audio_directory} и поместите туда MP3 файлы")
        return
    
    # Обрабатываем все файлы
    conversations = transcriber.process_directory(audio_directory)
    
    if conversations:
        # Экспортируем в Excel
        transcriber.export_to_excel(conversations)
        print(f"\nТранскрибация завершена! Результаты сохранены в transcribed_calls.xlsx")
    else:
        print("Не удалось обработать ни одного файла")


if __name__ == "__main__":
    main() 