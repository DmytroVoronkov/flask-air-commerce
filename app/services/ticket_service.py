from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError
from models import db, Ticket, FlightFare, Shift, ShiftStatus, CashDeskAccount, Transaction, TransactionType, ExchangeRate, TicketStatus
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

def sell_ticket(cashier_id, flight_id, flight_fare_id, passenger_name, seat_number, currency_code):
    """
    Продаж квитка з обробкою валюти, оновленням рахунків і створенням транзакції.
    """
    try:
        # Перевірка відкритої зміни
        shift = Shift.query.filter_by(cashier_id=cashier_id, status=ShiftStatus.OPEN).first()
        if not shift:
            return None, False, "Немає відкритої зміни для касира"

        # Перевірка рейсу та тарифу
        flight_fare = FlightFare.query.filter_by(id=flight_fare_id, flight_id=flight_id).first()
        if not flight_fare:
            return None, False, "Тариф не знайдено або не відповідає рейсу"
        
        if flight_fare.seats_sold >= flight_fare.seat_limit:
            return None, False, "Немає доступних місць для цього тарифу"

        # Перевірка унікальності номера місця
        if Ticket.query.filter_by(flight_id=flight_id, seat_number=seat_number).first():
            return None, False, "Це місце вже зайнято"

        # Отримання курсу обміну
        exchange_rate = ExchangeRate.query.filter_by(
            base_currency=flight_fare.base_currency,
            target_currency=currency_code
        ).order_by(ExchangeRate.valid_at.desc()).first()
        if not exchange_rate and flight_fare.base_currency != currency_code:
            return None, False, "Курс обміну для вказаної валюти не знайдено"

        # Конвертація ціни
        price_in_base = Decimal(str(flight_fare.base_price))
        exchange_rate_value = Decimal(str(exchange_rate.rate)) if exchange_rate else Decimal('1.0')
        if flight_fare.base_currency != currency_code:
            amount = price_in_base * exchange_rate_value
        else:
            amount = price_in_base

        # Пошук рахунку каси для валюти
        account = CashDeskAccount.query.filter_by(
            cash_desk_id=shift.cash_desk_id,
            currency_code=currency_code
        ).first()
        if not account:
            return None, False, f"Рахунок для валюти {currency_code} не знайдено"

        # Створення квитка
        logger.debug(f"Creating ticket with status: {TicketStatus.SOLD}")
        ticket = Ticket(
            flight_id=flight_id,
            flight_fare_id=flight_fare_id,
            shift_id=shift.id,
            passenger_name=passenger_name.strip(),
            seat_number=seat_number.strip(),
            price=amount,
            currency_code=currency_code,
            price_in_base=price_in_base,
            exchange_rate=exchange_rate_value,
            status=TicketStatus.SOLD
        )

        # Оновлення кількості проданих місць
        flight_fare.seats_sold += 1

        # Оновлення балансу рахунку
        account.balance = Decimal(str(account.balance)) + amount
        account.last_updated = datetime.now(timezone.utc)

        # Створення транзакції
        transaction = Transaction(
            shift_id=shift.id,
            account_id=account.id,
            type=TransactionType.SALE,
            amount=amount,
            currency_code=currency_code,
            reference_type='ticket',
            reference_id=ticket.id,
            description=f"Продаж квитка {ticket.seat_number} на рейс {flight_fare.flight.flight_number}"
        )

        db.session.add(ticket)
        db.session.add(transaction)
        db.session.commit()

        logger.info(f"Квиток {ticket.id} успішно продано для пасажира {passenger_name}")
        return {
            'id': ticket.id,
            'flight_number': flight_fare.flight.flight_number,
            'passenger_name': passenger_name,
            'seat_number': seat_number,
            'price': float(amount),
            'currency_code': currency_code
        }, True, None

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Помилка бази даних при продажі квитка: {e}")
        return None, False, "Помилка бази даних"
    except Exception as e:
        db.session.rollback()
        logger.error(f"Невідома помилка при продажі квитка: {e}")
        return None, False, f"Невідома помилка: {str(e)}"