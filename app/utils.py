from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def datetimeformat(value, format='%d.%m.%Y %H:%M'):
    """
    Форматує ISO-рядок дати у заданий формат (наприклад, 'дд.мм.рррр гг:хх').
    
    Args:
        value (str): ISO-рядок дати (наприклад, '2025-10-15T14:00:00+00:00')
        format (str): Формат виводу (за замовчуванням '%d.%m.%Y %H:%M')
    
    Returns:
        str: Відформатована дата або оригінальний рядок у разі помилки
    """
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return dt.strftime(format)
    except ValueError as e:
        logger.error(f"Error formatting datetime: {value}, error: {e}")
        return value  # Повертаємо оригінальний рядок, якщо формат некоректний