from models import Shift, ShiftStatus, db, CashDesk, CashDeskAccount, Transaction, TransactionType, Airport
from datetime import datetime, timedelta
import logging
logger = logging.getLogger(__name__)

def create_cash_desk(name, airport_id, is_active=True):
    try:
        if not Airport.query.get(airport_id):
            return None, False, "Аеропорт не знайдено"
        if CashDesk.query.filter_by(name=name, airport_id=airport_id).first():
            return None, False, f"Каса з назвою {name} уже існує в цьому аеропорту"
       
        cash_desk = CashDesk(name=name.strip(), airport_id=airport_id, is_active=is_active)
        db.session.add(cash_desk)
        db.session.commit()
        logger.info(f"Створено касу: {name}")
        return {
            'id': cash_desk.id,
            'name': cash_desk.name,
            'airport_id': cash_desk.airport_id,
            'is_active': cash_desk.is_active
        }, True, None
    except Exception as e:
        db.session.rollback()
        logger.error(f"Помилка створення каси: {e}")
        return None, False, "Не вдалося створити касу"

def create_cash_desk_account(cash_desk_id, currency_code):
    try:
        if not CashDesk.query.get(cash_desk_id):
            return None, False, "Касу не знайдено"
        if CashDeskAccount.query.filter_by(cash_desk_id=cash_desk_id, currency_code=currency_code).first():
            return None, False, f"Рахунок у валюті {currency_code} уже існує для цієї каси"
       
        account = CashDeskAccount(cash_desk_id=cash_desk_id, currency_code=currency_code.strip(), balance=0.0)
        db.session.add(account)
        db.session.commit()
        logger.info(f"Створено рахунок {currency_code} для каси {cash_desk_id}")
        return {
            'id': account.id,
            'cash_desk_id': account.cash_desk_id,
            'currency_code': account.currency_code,
            'balance': float(account.balance)
        }, True, None
    except Exception as e:
        db.session.rollback()
        logger.error(f"Помилка створення рахунку: {e}")
        return None, False, "Не вдалося створити рахунок"

def get_all_cash_desks():
    try:
        cash_desks = CashDesk.query.all()
        cash_desks_list = [
            {
                'id': cd.id,
                'name': cd.name,
                'airport_id': cd.airport_id,
                'airport_name': cd.airport.name if cd.airport else 'Не вказано',
                'is_active': cd.is_active
            } for cd in cash_desks
        ]
        logger.info(f"Отримано {len(cash_desks_list)} кас")
        return cash_desks_list, True, None
    except Exception as e:
        logger.error(f"Помилка отримання кас: {e}")
        return [], False, "Не вдалося отримати каси"

def update_cash_desk(cash_desk_id, name, airport_id, is_active):
    try:
        cash_desk = CashDesk.query.get(cash_desk_id)
        if not cash_desk:
            return False, "Касу не знайдено"
        if not Airport.query.get(airport_id):
            return False, "Аеропорт не знайдено"
        if CashDesk.query.filter_by(name=name, airport_id=airport_id).filter(CashDesk.id != cash_desk_id).first():
            return False, f"Каса з назвою {name} уже існує в цьому аеропорту"
       
        cash_desk.name = name.strip()
        cash_desk.airport_id = airport_id
        cash_desk.is_active = is_active
        db.session.commit()
        logger.info(f"Оновлено касу {cash_desk_id}")
        return True, None
    except Exception as e:
        db.session.rollback()
        logger.error(f"Помилка оновлення каси: {e}")
        return False, "Не вдалося оновити касу"

def get_cash_desk_accounts(cash_desk_id):
    try:
        cash_desk = CashDesk.query.get(cash_desk_id)
        if not cash_desk:
            return [], False, "Касу не знайдено"
        accounts = CashDeskAccount.query.filter_by(cash_desk_id=cash_desk_id).all()
        accounts_list = [
            {
                'id': account.id,
                'cash_desk_id': account.cash_desk_id,
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

def withdraw_from_cash_desk(shift_id, currency_code, amount):
    try:
        from decimal import Decimal
        amount = Decimal(str(amount))
       
        # Перевірка зміни
        shift = Shift.query.get(shift_id)
        if not shift or shift.status != ShiftStatus.OPEN:
            return None, False, "Зміна не відкрита"
       
        # Перевірка рахунку каси
        account = CashDeskAccount.query.filter_by(cash_desk_id=shift.cash_desk_id, currency_code=currency_code).first()
        if not account:
            return None, False, f"Рахунок у валюті {currency_code} не знайдено"
        if amount <= 0:
            return None, False, "Сума зняття має бути більше 0"
        if account.balance < amount:
            return None, False, "Недостатньо коштів на рахунку"
       
        account.balance -= amount
        account.last_updated = datetime.now()
        transaction = Transaction(
            shift_id=shift_id,
            account_id=account.id,
            type=TransactionType.WITHDRAWAL,
            amount=-amount,
            currency_code=currency_code,
            description="Зняття готівки"
        )
        db.session.add(transaction)
        db.session.commit()
        logger.info(f"Знято {amount} {currency_code} з каси {shift.cash_desk_id}")
        return {
            'cash_desk_id': shift.cash_desk_id,
            'currency_code': currency_code,
            'amount': float(amount),
            'new_balance': float(account.balance)
        }, True, None
    except Exception as e:
        db.session.rollback()
        logger.error(f"Помилка зняття з каси {shift.cash_desk_id}: {e}")
        return None, False, "Не вдалося виконати зняття"

def get_cash_desk_balances_by_date(airport_id, cash_desk_id, date1, date2=None):
    """Отримує баланси кас за одну або дві дати."""
    try:
        # Перевірка аеропорту
        airport = Airport.query.get(airport_id)
        if not airport:
            return [], False, "Аеропорт не знайдено"
        # Визначаємо каси для запиту
        if cash_desk_id:
            cash_desks = [CashDesk.query.get(cash_desk_id)]
            if not cash_desks[0]:
                return [], False, "Касу не знайдено"
        else:
            cash_desks = CashDesk.query.filter_by(airport_id=airport_id, is_active=True).all()
            if not cash_desks:
                return [], False, "Каси не знайдені для цього аеропорту"
        balances = []
        for cash_desk in cash_desks:
            accounts = CashDeskAccount.query.filter_by(cash_desk_id=cash_desk.id).all()
            for account in accounts:
                # Отримуємо баланс на кінець date1
                balance_date1 = db.session.query(
                    db.func.sum(Transaction.amount)
                ).filter(
                    Transaction.account_id == account.id,
                    Transaction.created_at <= datetime.combine(date1, datetime.max.time())
                ).scalar() or 0.0
                balance_date2 = None
                difference = None
                if date2:
                    # Отримуємо баланс на кінець date2
                    balance_date2 = db.session.query(
                        db.func.sum(Transaction.amount)
                    ).filter(
                        Transaction.account_id == account.id,
                        Transaction.created_at <= datetime.combine(date2, datetime.max.time())
                    ).scalar() or 0.0
                    difference = balance_date1 - balance_date2
                balances.append({
                    'cash_desk_id': cash_desk.id,
                    'cash_desk_name': cash_desk.name,
                    'currency_code': account.currency_code,
                    'balance_date1': round(float(balance_date1), 2),
                    'balance_date2': round(float(balance_date2), 2) if balance_date2 is not None else None,
                    'difference': round(float(difference), 2) if difference is not None else None
                })
        logger.info(f"Отримано баланси для {len(balances)} рахунків кас аеропорту {airport_id}")
        return balances, True, None
    except Exception as e:
        logger.error(f"Помилка отримання балансів для аеропорту {airport_id}: {e}")
        return [], False, f"Не вдалося отримати баланси: {e}"