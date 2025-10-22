from datetime import datetime
import logging
from flask import current_app

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
            return str(value)
    except ValueError as e:
        logger.error(f"Error formatting datetime: {value}, error: {e}")
        return str(value)

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
        'sale': 'Продаж',
        'refund': 'Повернення',
        'deposit': 'Поповнення',
        'withdrawal': 'Зняття'
    }
    return translations.get(value, value)

def floatformat(value, precision=2):
    """
    Форматує число з плаваючою точкою до заданого числа знаків після коми.
   
    Args:
        value (float or int or None): Число для форматування або None
        precision (int): Кількість знаків після коми (за замовчуванням 2)
   
    Returns:
        str: Відформатоване число як рядок або 'Н/Д' для None
    """
    if value is None:
        return 'Н/Д'
    try:
        return f"{float(value):.{precision}f}"
    except (ValueError, TypeError):
        logger.error(f"Error formatting float: {value}")
        return str(value)

# Реєстрація фільтрів у Flask
def register_filters(app):
    app.jinja_env.filters['datetimeformat'] = datetimeformat
    app.jinja_env.filters['transaction_type_ua'] = transaction_type_ua
    app.jinja_env.filters['floatformat'] = floatformat