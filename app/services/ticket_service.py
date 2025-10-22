from models import CashDesk, db, Ticket, TicketStatus, Flight, FlightFare, Shift, ShiftStatus, CashDeskAccount, Transaction, TransactionType, ExchangeRate
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import logging
logger = logging.getLogger(__name__)

def sell_ticket(shift_id, flight_id, flight_fare_id, passenger_name, seat_number, currency_code):
    try:
        # Перевірка вхідних даних
        if not all([shift_id, flight_id, flight_fare_id, passenger_name, seat_number, currency_code]):
            return None, False, "Усі поля є обов’язковими"
        shift = Shift.query.get(shift_id)
        if not shift or shift.status != ShiftStatus.OPEN:
            return None, False, "Зміна не відкрита"
        flight = Flight.query.get(flight_id)
        if not flight:
            return None, False, "Рейс не знайдено"
        flight_fare = FlightFare.query.get(flight_fare_id)
        if not flight_fare or flight_fare.flight_id != flight_id:
            return None, False, "Тариф не знайдено або не відповідає рейсу"
        # Перевірка доступності місця
        if Ticket.query.filter_by(flight_id=flight_id, seat_number=seat_number, status=TicketStatus.SOLD).first():
            return None, False, f"Місце {seat_number} уже зайнято"
        # Перевірка ліміту місць
        if flight_fare.seats_sold >= flight_fare.seat_limit:
            return None, False, f"Ліміт місць для тарифу {flight_fare.name} вичерпано"
        # Перевірка наявності рахунку в касі
        cash_desk_account = CashDeskAccount.query.filter_by(
            cash_desk_id=shift.cash_desk_id, currency_code=currency_code
        ).first()
        if not cash_desk_account:
            return None, False, f"Рахунок у валюті {currency_code} не знайдено для каси"
        # Обчислення ціни в базовій валюті (USD)
        price_in_base = Decimal(str(flight_fare.base_price))
        exchange_rate = Decimal('1.0')
        price = price_in_base
        if currency_code != flight_fare.base_currency:
            exchange = ExchangeRate.query.filter_by(
                base_currency=flight_fare.base_currency,
                target_currency=currency_code
            ).order_by(ExchangeRate.valid_at.desc()).first()
            if not exchange:
                return None, False, f"Курс обміну з {flight_fare.base_currency} на {currency_code} не знайдено"
            exchange_rate = Decimal(str(exchange.rate))
            price = price_in_base * exchange_rate
        # Створення квитка
        ticket = Ticket(
            flight_id=flight_id,
            flight_fare_id=flight_fare_id,
            shift_id=shift_id,
            passenger_name=passenger_name.strip(),
            seat_number=seat_number.strip(),
            price=price,
            currency_code=currency_code,
            price_in_base=price_in_base,
            exchange_rate=exchange_rate,
            status=TicketStatus.SOLD
        )
        flight_fare.seats_sold += 1
        cash_desk_account.balance += price
        cash_desk_account.last_updated = datetime.now(timezone.utc)
        # Створення транзакції
        transaction = Transaction(
            shift_id=shift_id,
            account_id=cash_desk_account.id,
            type=TransactionType.SALE,
            amount=price,
            currency_code=currency_code,
            reference_type='ticket',
            reference_id=ticket.id,
            description=f"Продаж квитка для пасажира {passenger_name}"
        )
        db.session.add(ticket)
        db.session.add(transaction)
        db.session.commit()
        logger.info(f"Продано квиток {ticket.id} для рейсу {flight.flight_number}")
        return {
            'id': ticket.id,
            'flight_id': ticket.flight_id,
            'flight_number': flight.flight_number,
            'passenger_name': ticket.passenger_name,
            'seat_number': ticket.seat_number,
            'price': float(ticket.price),
            'currency_code': ticket.currency_code,
            'sold_at': ticket.sold_at.isoformat()
        }, True, None
    except Exception as e:
        db.session.rollback()
        logger.error(f"Помилка продажу квитка: {e}")
        return None, False, f"Не вдалося продати квиток: {e}"

def refund_ticket(ticket_id):
    try:
        ticket = Ticket.query.get(ticket_id)
        if not ticket:
            return None, False, "Квиток не знайдено"
        if ticket.status != TicketStatus.SOLD:
            return None, False, "Квиток не може бути повернутий"
        shift = Shift.query.get(ticket.shift_id)
        if not shift or shift.status != ShiftStatus.OPEN:
            return None, False, "Зміна не відкрита"
        flight_fare = FlightFare.query.get(ticket.flight_fare_id)
        if not flight_fare:
            return None, False, "Тариф не знайдено"
        cash_desk_account = CashDeskAccount.query.filter_by(
            cash_desk_id=shift.cash_desk_id, currency_code=ticket.currency_code
        ).first()
        if not cash_desk_account:
            return None, False, f"Рахунок у валюті {ticket.currency_code} не знайдено для каси"
        if cash_desk_account.balance < ticket.price:
            return None, False, "Недостатньо коштів на рахунку каси для повернення"
        ticket.status = TicketStatus.REFUNDED
        flight_fare.seats_sold -= 1
        cash_desk_account.balance -= ticket.price
        cash_desk_account.last_updated = datetime.now(timezone.utc)
        transaction = Transaction(
            shift_id=shift.id,
            account_id=cash_desk_account.id,
            type=TransactionType.REFUND,
            amount=-Decimal(str(ticket.price)),
            currency_code=ticket.currency_code,
            reference_type='ticket',
            reference_id=ticket.id,
            description=f"Повернення квитка для пасажира {ticket.passenger_name}"
        )
        db.session.add(transaction)
        db.session.commit()
        logger.info(f"Повернено квиток {ticket.id} для рейсу {ticket.flight.flight_number}")
        return {
            'ticket_id': ticket.id,
            'passenger_name': ticket.passenger_name,
            'amount': float(ticket.price),
            'currency_code': ticket.currency_code,
            'status': ticket.status.value
        }, True, None
    except Exception as e:
        db.session.rollback()
        logger.error(f"Помилка повернення квитка {ticket_id}: {e}")
        return None, False, f"Не вдалося повернути квиток: {e}"

def get_sold_tickets_by_criteria(criteria):
    """Отримує продані квитки за заданими критеріями."""
    try:
        query = Ticket.query.filter_by(status=TicketStatus.SOLD)
        if 'flight_id' in criteria:
            query = query.filter_by(flight_id=criteria['flight_id'])
        elif 'airport_id' in criteria:
            query = query.join(Shift).join(CashDesk).filter(CashDesk.airport_id == criteria['airport_id'])
        elif 'cash_desk_id' in criteria:
            query = query.join(Shift).filter(Shift.cash_desk_id == criteria['cash_desk_id'])
        elif 'day' in criteria:
            start_time = datetime.combine(criteria['day'], datetime.min.time())
            end_time = start_time + timedelta(days=1)
            query = query.filter(Ticket.sold_at >= start_time, Ticket.sold_at < end_time)
        elif 'month' in criteria:
            start_time = datetime.combine(criteria['month'], datetime.min.time())
            next_month = (start_time.replace(day=28) + timedelta(days=4)).replace(day=1)
            query = query.filter(Ticket.sold_at >= start_time, Ticket.sold_at < next_month)
        elif 'start_date' in criteria and 'end_date' in criteria:
            start_time = datetime.combine(criteria['start_date'], datetime.min.time())
            end_time = datetime.combine(criteria['end_date'], datetime.max.time())
            query = query.filter(Ticket.sold_at >= start_time, Ticket.sold_at <= end_time)
        tickets = query.all()
        tickets_list = [
            {
                'id': ticket.id,
                'flight': {
                    'flight_number': ticket.flight.flight_number,
                    'origin_airport': ticket.flight.origin_airport.code,
                    'destination_airport': ticket.flight.destination_airport.code
                },
                'passenger_name': ticket.passenger_name,
                'flight_fare': {'name': ticket.flight_fare.name},
                'seat_number': ticket.seat_number,
                'price': float(ticket.price),
                'currency_code': ticket.currency_code,
                'shift': {'cash_desk': {'name': ticket.shift.cash_desk.name}},
                'sold_at': ticket.sold_at
            } for ticket in tickets
        ]
        logger.info(f"Отримано {len(tickets_list)} проданих квитків за критеріями: {criteria}")
        return tickets_list, True, None
    except Exception as e:
        logger.error(f"Помилка отримання квитків: {e}")
        return [], False, f"Не вдалося отримати квитки: {e}"