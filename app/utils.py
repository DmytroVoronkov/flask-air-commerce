from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def datetimeformat(value, format='%d.%m.%Y %H:%M'):
    """
    Форматує ISO-рядок дати або об’єкт datetime у заданий формат (наприклад, 'дд.мм.рррр гг:хх').
    
    Args:
        value (str or datetime): ISO-рядок дати (наприклад, '2025-10-15T14:00:00+00:00') або об’єкт datetime
        format (str): Формат виводу (за замовчуванням '%d.%m.%Y %H:%M')
    
    Returns:
        str: Відформатована дата або оригінальне значення у разі помилки
    """
    try:
        if isinstance(value, datetime):
            return value.strftime(format)
        elif isinstance(value, str):
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return dt.strftime(format)
        else:
            logger.error(f"Invalid type for datetimeformat: {type(value)}")
            return str(value)  # Повертаємо строкове представлення, якщо тип некоректний
    except ValueError as e:
        logger.error(f"Error formatting datetime: {value}, error: {e}")
        return str(value)  # Повертаємо оригінальне значення, якщо формат некоректний

def transaction_type_ua(value):
    """
    Переводить тип транзакції на українську мову.
    
    Args:
        value (str): Тип транзакції (SALE, REFUND, DEPOSIT, WITHDRAWAL або sale, refund, deposit, withdrawal)
    
    Returns:
        str: Перекладений тип транзакції українською мовою
    """
    translations = {
        'SALE': 'Продаж',
        'REFUND': 'Повернення',
        'DEPOSIT': 'Поповнення',
        'WITHDRAWAL': 'Зняття',
        # Підтримка старих значень в нижньому регістрі
        'sale': 'Продаж',
        'refund': 'Повернення',
        'deposit': 'Поповнення',
        'withdrawal': 'Зняття'
    }
    return translations.get(value, value)  # Повертаємо оригінальне значення, якщо переклад не знайдено