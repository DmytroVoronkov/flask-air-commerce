from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError
from models import db, CashDesk, Airport, CashDeskAccount, Transaction, TransactionType, Shift, ShiftStatus
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

def create_cash_desk(name, airport_id, is_active=True):
    try:
        cash_desk = CashDesk(name=name, airport_id=airport_id, is_active=is_active)
        db.session.add(cash_desk)
        db.session.commit()
        logger.info(f"Cash desk created: {name} for airport_id: {airport_id}")
        return cash_desk, True, None
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Error creating cash desk: {e}")
        return None, False, str(e)

def update_cash_desk(cash_desk_id, name, airport_id, is_active):
    try:
        cash_desk = CashDesk.query.get(cash_desk_id)
        if not cash_desk:
            return False, "Cash desk not found"
        cash_desk.name = name
        cash_desk.airport_id = airport_id
        cash_desk.is_active = is_active
        db.session.commit()
        logger.info(f"Cash desk updated: {cash_desk_id}")
        return True, None
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Error updating cash desk: {e}")
        return False, str(e)

def get_all_cash_desks():
    try:
        cash_desks = CashDesk.query.all()
        cash_desks_list = [
            {
                'id': cd.id,
                'name': cd.name,
                'airport_id': cd.airport_id,
                'airport_name': cd.airport.name if cd.airport else 'Unknown',
                'is_active': cd.is_active
            } for cd in cash_desks
        ]
        return cash_desks_list, True, None
    except SQLAlchemyError as e:
        logger.error(f"Error retrieving cash desks: {e}")
        return [], False, str(e)

def get_cash_desk_accounts(cash_desk_id):
    try:
        accounts = CashDeskAccount.query.filter_by(cash_desk_id=cash_desk_id).all()
        accounts_list = [
            {
                'id': acc.id,
                'currency_code': acc.currency_code,
                'balance': float(acc.balance),
                'last_updated': acc.last_updated.isoformat()
            } for acc in accounts
        ]
        return accounts_list, True, None
    except SQLAlchemyError as e:
        logger.error(f"Error retrieving cash desk accounts: {e}")
        return [], False, str(e)

def create_cash_desk_account(cash_desk_id, currency_code):
    try:
        existing_account = CashDeskAccount.query.filter_by(cash_desk_id=cash_desk_id, currency_code=currency_code).first()
        if existing_account:
            return None, False, f"Account with currency {currency_code} already exists for cash desk {cash_desk_id}"
        
        account = CashDeskAccount(
            cash_desk_id=cash_desk_id,
            currency_code=currency_code,
            balance=Decimal('0.0'),
            last_updated=datetime.now(timezone.utc)
        )
        db.session.add(account)
        db.session.commit()
        logger.info(f"Cash desk account created: {currency_code} for cash_desk_id: {cash_desk_id}")
        return account, True, None
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Error creating cash desk account: {e}")
        return None, False, str(e)

def withdraw_from_cash_desk(cashier_id, cash_desk_id, currency_code, amount):
    """
    Зняття грошей з рахунку каси касиром.
    """
    try:
        # Перевірка відкритої зміни
        shift = Shift.query.filter_by(cashier_id=cashier_id, status=ShiftStatus.OPEN).first()
        if not shift:
            return None, False, "Немає відкритої зміни для касира"

        # Перевірка, що зміна відповідає касі
        if shift.cash_desk_id != cash_desk_id:
            return None, False, "Касир не працює на цій касі"

        # Пошук рахунку каси
        account = CashDeskAccount.query.filter_by(
            cash_desk_id=cash_desk_id,
            currency_code=currency_code
        ).first()
        if not account:
            return None, False, f"Рахунок для валюти {currency_code} не знайдено"

        # Перевірка достатності балансу
        amount = Decimal(str(amount))
        if amount <= 0:
            return None, False, "Сума зняття має бути більшою за 0"
        if account.balance < amount:
            return None, False, f"Недостатньо коштів на рахунку ({account.balance} {currency_code})"

        # Оновлення балансу
        account.balance -= amount
        account.last_updated = datetime.now(timezone.utc)

        # Створення транзакції
        transaction = Transaction(
            shift_id=shift.id,
            account_id=account.id,
            type=TransactionType.WITHDRAWAL,
            amount=-amount,
            currency_code=currency_code,
            reference_type='withdrawal',
            reference_id=None,
            description=f"Зняття {amount} {currency_code} касиром {cashier_id}",
            created_at=datetime.now(timezone.utc)
        )

        db.session.add(transaction)
        db.session.commit()

        logger.info(f"Withdrawal of {amount} {currency_code} from cash desk {cash_desk_id} by cashier {cashier_id}")
        return {
            'cash_desk_id': cash_desk_id,
            'currency_code': currency_code,
            'amount': float(amount),
            'new_balance': float(account.balance)
        }, True, None

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error during withdrawal: {e}")
        return None, False, "Помилка бази даних"
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error during withdrawal: {e}")
        return None, False, f"Невідома помилка: {str(e)}"