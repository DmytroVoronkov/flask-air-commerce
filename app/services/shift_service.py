from models import Shift, CashDesk, Role, User, ShiftStatus
from datetime import datetime, timezone
import logging
logger = logging.getLogger(__name__)

def get_available_cash_desks(airport_id):
    """
    Отримує список активних кас без відкритих змін для аеропорту.
   
    Args:
        airport_id (int): ID аеропорту
   
    Returns:
        tuple: (cash_desks: list, success: bool, error_message: str)
    """
    try:
        active_cash_desks = CashDesk.query.filter_by(airport_id=airport_id, is_active=True).all()
        open_shifts = Shift.query.filter_by(status=ShiftStatus.OPEN).all()
        open_cash_desk_ids = {shift.cash_desk_id for shift in open_shifts}
        available_cash_desks = [
            {'id': desk.id, 'name': desk.name}
            for desk in active_cash_desks
            if desk.id not in open_cash_desk_ids
        ]
        logger.info(f"Отримано {len(available_cash_desks)} вільних кас для аеропорту {airport_id}")
        return available_cash_desks, True, None
    except Exception as e:
        logger.error(f"Помилка отримання вільних кас для аеропорту {airport_id}: {e}")
        return [], False, "Не вдалося отримати список кас"

def open_shift(user_id, cash_desk_id):
    """
    Відкриває нову зміну для касира на вказаній касі.
   
    Args:
        user_id (int): ID касира
        cash_desk_id (int): ID каси
   
    Returns:
        tuple: (shift_data: dict, success: bool, error_message: str)
    """
    try:
        user = User.query.get(user_id)
        if not user or user.role != Role.CASHIER:
            return {}, False, "Тільки касири можуть відкривати зміни"
        if not user.airport_id:
            return {}, False, "Касир не прив’язаний до аеропорту"
        cash_desk = CashDesk.query.get(cash_desk_id)
        if not cash_desk or cash_desk.airport_id != user.airport_id or not cash_desk.is_active:
            return {}, False, "Каса недоступна або не належить вашому аеропорту"
        open_shift = Shift.query.filter_by(cashier_id=user_id, status=ShiftStatus.OPEN).first()
        if open_shift:
            return {}, False, f"У вас уже є відкрита зміна (ID: {open_shift.id})"
        open_shift = Shift.query.filter_by(cash_desk_id=cash_desk_id, status=ShiftStatus.OPEN).first()
        if open_shift:
            return {}, False, f"Каса {cash_desk.name} уже використовується в іншій зміні"
        new_shift = Shift(
            cash_desk_id=cash_desk_id,
            cashier_id=user_id,
            opened_at=datetime.now(timezone.utc),
            status=ShiftStatus.OPEN
        )
        Shift.query.session.add(new_shift)
        Shift.query.session.commit()
        logger.info(f"User {user_id} opened shift {new_shift.id} on cash desk {cash_desk_id}")
        return {'shift_id': new_shift.id, 'cash_desk_name': cash_desk.name}, True, None
    except Exception as e:
        Shift.query.session.rollback()
        logger.error(f"Error opening shift for user {user_id}: {e}")
        return {}, False, "Не вдалося відкрити зміну"

def close_shift(user_id):
    """
    Закриває відкриту зміну касира.
   
    Args:
        user_id (int): ID касира
   
    Returns:
        tuple: (shift_data: dict, success: bool, error_message: str)
    """
    try:
        open_shift = Shift.query.filter_by(cashier_id=user_id, status=ShiftStatus.OPEN).first()
        if not open_shift:
            return {}, False, "Немає відкритої зміни"
        open_shift.status = ShiftStatus.CLOSED
        open_shift.closed_at = datetime.now(timezone.utc)
        Shift.query.session.commit()
        logger.info(f"User {user_id} closed shift {open_shift.id}")
        return {'shift_id': open_shift.id}, True, None
    except Exception as e:
        Shift.query.session.rollback()
        logger.error(f"Error closing shift for user {user_id}: {e}")
        return {}, False, "Не вдалося закрити зміну"