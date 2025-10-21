from datetime import datetime, timezone
from models import CashDesk, Airport, CashDeskAccount
from sqlalchemy.exc import IntegrityError
from database import db
import logging

logger = logging.getLogger(__name__)

def get_all_cash_desks():
    """
    Отримує список всіх кас.
  
    Returns:
        tuple: (cash_desks_list: list, success: bool, error_message: str)
    """
    try:
        cash_desks = CashDesk.query.all()
        cash_desks_list = [
            {
                'id': cash_desk.id,
                'name': cash_desk.name,
                'airport_id': cash_desk.airport_id,
                'airport_name': cash_desk.airport.name if cash_desk.airport else 'Не вказано',
                'is_active': cash_desk.is_active
            } for cash_desk in cash_desks
        ]
        logger.info(f"Отримано {len(cash_desks_list)} кас")
        return cash_desks_list, True, None
    except Exception as e:
        logger.error(f"Помилка отримання кас: {e}")
        return [], False, "Не вдалося отримати каси"

def create_cash_desk(name, airport_id, is_active=True):
    """
    Створює нову касу.
  
    Args:
        name (str): Назва каси
        airport_id (int): ID аеропорту
        is_active (bool): Статус активності
  
    Returns:
        tuple: (cash_desk: dict, success: bool, error_message: str)
    """
    try:
        if not Airport.query.get(airport_id):
            return {}, False, "Аеропорт не знайдено"
        cash_desk = CashDesk(
            name=name.strip(),
            airport_id=airport_id,
            is_active=is_active
        )
        CashDesk.query.session.add(cash_desk)
        CashDesk.query.session.commit()
        logger.info(f"Створено касу: {name}")
        return {
            'id': cash_desk.id,
            'name': cash_desk.name,
            'airport_id': cash_desk.airport_id,
            'is_active': cash_desk.is_active
        }, True, None
    except IntegrityError:
        CashDesk.query.session.rollback()
        logger.error(f"Помилка створення каси: Каса з такою назвою вже існує")
        return {}, False, "Каса з такою назвою вже існує"
    except Exception as e:
        CashDesk.query.session.rollback()
        logger.error(f"Помилка створення каси: {e}")
        return {}, False, "Не вдалося створити касу"

def update_cash_desk(cash_desk_id, name, airport_id, is_active):
    """
    Оновлює касу.
  
    Args:
        cash_desk_id (int): ID каси
        name (str): Нова назва каси
        airport_id (int): Новий ID аеропорту
        is_active (bool): Новий статус активності
  
    Returns:
        tuple: (success: bool, error_message: str)
    """
    try:
        cash_desk = CashDesk.query.get(cash_desk_id)
        if not cash_desk:
            return False, "Касу не знайдено"
        if not Airport.query.get(airport_id):
            return False, "Аеропорт не знайдено"
        cash_desk.name = name.strip()
        cash_desk.airport_id = airport_id
        cash_desk.is_active = is_active
        CashDesk.query.session.commit()
        logger.info(f"Оновлено касу: {cash_desk_id}")
        return True, None
    except IntegrityError:
        CashDesk.query.session.rollback()
        logger.error(f"Помилка оновлення каси: Каса з такою назвою вже існує")
        return False, "Каса з такою назвою вже існує"
    except Exception as e:
        CashDesk.query.session.rollback()
        logger.error(f"Помилка оновлення каси: {e}")
        return False, "Не вдалося оновити касу"

def create_cash_desk_account(cash_desk_id, currency_code):
    """
    Створює новий рахунок для каси у вказаній валюті.
  
    Args:
        cash_desk_id (int): ID каси
        currency_code (str): Код валюти (наприклад, USD, EUR, UAH)
  
    Returns:
        tuple: (account: dict, success: bool, error_message: str)
    """
    from database import db
    try:
        if not CashDesk.query.get(cash_desk_id):
            return {}, False, "Касу не знайдено"
        if not currency_code in ['USD', 'EUR', 'UAH']:
            return {}, False, "Непідтримувана валюта. Дозволені: USD, EUR, UAH"
        existing_account = CashDeskAccount.query.filter_by(cash_desk_id=cash_desk_id, currency_code=currency_code).first()
        if existing_account:
            return {}, False, f"Рахунок у валюті {currency_code} уже існує для цієї каси"
        account = CashDeskAccount(
            cash_desk_id=cash_desk_id,
            currency_code=currency_code,
            balance=0.0,
            last_updated=datetime.now(timezone.utc)
        )
        db.session.add(account)
        db.session.commit()
        logger.info(f"Створено рахунок {currency_code} для каси {cash_desk_id}")
        return {
            'id': account.id,
            'cash_desk_id': account.cash_desk_id,
            'currency_code': account.currency_code,
            'balance': float(account.balance),
            'last_updated': account.last_updated.isoformat()
        }, True, None
    except Exception as e:
        db.session.rollback()
        logger.error(f"Помилка створення рахунку для каси {cash_desk_id}: {e}")
        return {}, False, "Не вдалося створити рахунок"

def get_cash_desk_accounts(cash_desk_id):
    """
    Отримує список усіх рахунків для каси.
  
    Args:
        cash_desk_id (int): ID каси
  
    Returns:
        tuple: (accounts_list: list, success: bool, error_message: str)
    """
    try:
        if not CashDesk.query.get(cash_desk_id):
            return [], False, "Касу не знайдено"
        accounts = CashDeskAccount.query.filter_by(cash_desk_id=cash_desk_id).all()
        accounts_list = [
            {
                'id': account.id,
                'currency_code': account.currency_code,
                'balance': float(account.balance),
                'last_updated': account.last_updated.isoformat()
            } for account in accounts
        ]
        logger.info(f"Отримано {len(accounts_list)} рахунків для каси {cash_desk_id}")
        return accounts_list, True, None
    except Exception as e:
        logger.error(f"Помилка отримання рахунків для каси {cash_desk_id}: {e}")
        return [], False, "Не вдалося отримати рахунки"