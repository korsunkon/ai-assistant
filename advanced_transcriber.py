import os
import openai
import pandas as pd
from pathlib import Path
import json
from typing import List, Dict, Any
import logging
import re

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedCallTranscriber:
    def __init__(self, api_key: str):
        """Инициализация продвинутого транскрибера с API ключом OpenAI"""
        self.client = openai.OpenAI(api_key=api_key)
        
        # Ключевые слова для определения ролей
        self.manager_keywords = [
            'здравствуйте', 'добрый день', 'добрый вечер', 'доброе утро',
            'спасибо за звонок', 'чем могу помочь', 'как вас зовут',
            'ваш номер телефона', 'адрес доставки', 'стоимость услуги',
            'условия договора', 'сроки выполнения', 'гарантия',
            'до свидания', 'хорошего дня', 'обращайтесь'
        ]
        
        self.client_keywords = [
            'хочу заказать', 'интересует', 'сколько стоит', 'когда будет готово',
            'можно ли', 'есть ли скидка', 'как оплатить', 'где забрать',
            'да', 'нет', 'хорошо', 'понятно', 'спасибо', 'до свидания'
        ]
        
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
    
    def analyze_conversation_flow(self, segments: List[Dict]) -> List[Dict[str, str]]:
        """
        Анализирует поток разговора для лучшего определения ролей
        """
        conversations = []
        
        for i, segment in enumerate(segments):
            text = segment.get('text', '').strip()
            if not text:
                continue
            
            # Анализируем контекст разговора
            role = self._determine_role_advanced(text, i, segments)
            
            conversations.append({
                'text': text,
                'role': role,
                'start_time': segment.get('start', 0),
                'end_time': segment.get('end', 0)
            })
        
        return conversations
    
    def _determine_role_advanced(self, text: str, segment_index: int, all_segments: List[Dict]) -> str:
        """
        Продвинутое определение роли на основе контекста и ключевых слов
        """
        text_lower = text.lower()
        
        # Подсчитываем баллы для каждой роли
        manager_score = 0
        client_score = 0
        
        # Проверяем ключевые слова менеджера
        for keyword in self.manager_keywords:
            if keyword in text_lower:
                manager_score += 2
        
        # Проверяем ключевые слова клиента
        for keyword in self.client_keywords:
            if keyword in text_lower:
                client_score += 2
        
        # Анализируем контекст (первая реплика обычно менеджер)
        if segment_index == 0:
            manager_score += 3
        
        # Анализируем длину реплики (менеджеры обычно говорят больше)
        if len(text.split()) > 10:
            manager_score += 1
        
        # Анализируем предыдущие реплики
        if segment_index > 0:
            prev_text = all_segments[segment_index - 1].get('text', '').lower()
            if any(word in prev_text for word in ['вопрос', 'заказ', 'услуга']):
                client_score += 1
        
        # Определяем роль по баллам
        if manager_score > client_score:
            return 'Менеджер'
        elif client_score > manager_score:
            return 'Клиент'
        else:
            return 'Неопределено'
    
    def process_transcript(self, transcript: Dict[str, Any], manager_name: str) -> List[Dict[str, str]]:
        """
        Обрабатывает транскрипт и извлекает реплики с ролями
        """
        conversations = []
        
        if not transcript or 'segments' not in transcript:
            logger.warning(f"Нет сегментов в транскрипте для {manager_name}")
            return conversations
        
        # Анализируем поток разговора
        conversation_flow = self.analyze_conversation_flow(transcript['segments'])
        
        for conv in conversation_flow:
            conversations.append({
                'manager_name': manager_name,
                'role': conv['role'],
                'replica': conv['text'],
                'start_time': conv['start_time'],
                'end_time': conv['end_time']
            })
        
        return conversations
    
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
    
    def export_to_excel(self, conversations: List[Dict[str, str]], output_file: str = "transcribed_calls_advanced.xlsx"):
        """
        Экспортирует результаты в Excel файл с дополнительной информацией
        """
        if not conversations:
            logger.warning("Нет данных для экспорта")
            return
        
        # Создаем DataFrame
        df = pd.DataFrame(conversations)
        
        # Сортируем по времени начала
        if 'start_time' in df.columns:
            df = df.sort_values(['manager_name', 'start_time'])
        
        # Создаем Excel файл с несколькими листами
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Основной лист
            df.to_excel(writer, sheet_name='Все реплики', index=False)
            
            # Сводка по менеджерам
            manager_summary = df.groupby('manager_name').agg({
                'replica': 'count',
                'role': lambda x: x.value_counts().to_dict()
            }).reset_index()
            manager_summary.columns = ['Имя менеджера', 'Всего реплик', 'Распределение ролей']
            manager_summary.to_excel(writer, sheet_name='Сводка по менеджерам', index=False)
            
            # Статистика по ролям
            role_stats = df['role'].value_counts().reset_index()
            role_stats.columns = ['Роль', 'Количество реплик']
            role_stats.to_excel(writer, sheet_name='Статистика ролей', index=False)
        
        logger.info(f"Результаты экспортированы в {output_file}")
        logger.info(f"Всего реплик: {len(conversations)}")
        
        # Показываем статистику
        print(f"\nСтатистика транскрибации:")
        print(f"Всего реплик: {len(conversations)}")
        print(f"Менеджеров: {df['manager_name'].nunique()}")
        print(f"Распределение ролей:")
        role_counts = df['role'].value_counts()
        for role, count in role_counts.items():
            print(f"  {role}: {count}")


def main():
    """
    Основная функция для запуска продвинутой транскрибации
    """
    # Получаем API ключ из переменной окружения
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        logger.error("Не установлена переменная окружения OPENAI_API_KEY")
        print("Пожалуйста, установите переменную окружения OPENAI_API_KEY")
        print("Пример: set OPENAI_API_KEY=your_api_key_here")
        return
    
    # Создаем транскрибер
    transcriber = AdvancedCallTranscriber(api_key)
    
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
        print(f"\nТранскрибация завершена! Результаты сохранены в transcribed_calls_advanced.xlsx")
    else:
        print("Не удалось обработать ни одного файла")


if __name__ == "__main__":
    main() 