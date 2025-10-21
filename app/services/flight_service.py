from models import Flight, FlightFare, Airport
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
from database import db
import logging

logger = logging.getLogger(__name__)

def create_flight(flight_number, origin_airport_id, destination_airport_id, departure_time, arrival_time, aircraft_model, seat_capacity):
    """
    Створює новий рейс.
    
    Args:
        flight_number (str): Номер рейсу
        origin_airport_id (int): ID аеропорту відправлення
        destination_airport_id (int): ID аеропорту призначення
        departure_time (str): Час відправлення (формат datetime-local або ISO)
        arrival_time (str): Час прибуття (формат datetime-local або ISO)
        aircraft_model (str): Модель літака
        seat_capacity (int): Місткість місць
    
    Returns:
        tuple: (flight: dict, success: bool, error_message: str)
    """
    try:
        if not all([flight_number, origin_airport_id, destination_airport_id, departure_time, arrival_time, aircraft_model, seat_capacity]):
            return {}, False, "Заповніть усі поля"
        if origin_airport_id == destination_airport_id:
            return {}, False, "Аеропорт відправлення та призначення не можуть бути однаковими"
        if not Airport.query.get(origin_airport_id):
            return {}, False, "Аеропорт відправлення не знайдено"
        if not Airport.query.get(destination_airport_id):
            return {}, False, "Аеропорт призначення не знайдено"
        
        # Конвертація вхідних дат у datetime з часовим поясом UTC
        try:
            # datetime-local надсилає формат типу "2025-11-01T10:00"
            departure_time_dt = datetime.fromisoformat(departure_time.replace('Z', '')) if departure_time.endswith('Z') else datetime.fromisoformat(departure_time)
            arrival_time_dt = datetime.fromisoformat(arrival_time.replace('Z', '')) if arrival_time.endswith('Z') else datetime.fromisoformat(arrival_time)
            # Явно встановлюємо часовий пояс UTC
            departure_time_dt = departure_time_dt.replace(tzinfo=timezone.utc)
            arrival_time_dt = arrival_time_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return {}, False, "Невірний формат дати"
        
        # Перевірка часу
        now_utc = datetime.now(timezone.utc)
        if departure_time_dt < now_utc:
            return {}, False, "Час відправлення не може бути в минулому"
        if arrival_time_dt <= departure_time_dt:
            return {}, False, "Час прибуття має бути пізніше часу відправлення"
        if seat_capacity <= 0:
            return {}, False, "Місткість місць має бути більше 0"
        
        flight = Flight(
            flight_number=flight_number.strip(),
            origin_airport_id=origin_airport_id,
            destination_airport_id=destination_airport_id,
            departure_time=departure_time_dt,
            arrival_time=arrival_time_dt,
            aircraft_model=aircraft_model.strip(),
            seat_capacity=seat_capacity
        )
        db.session.add(flight)
        db.session.commit()
        logger.info(f"Створено рейс: {flight_number}")
        return {
            'id': flight.id,
            'flight_number': flight.flight_number,
            'origin_airport_id': flight.origin_airport_id,
            'destination_airport_id': flight.destination_airport_id,
            'departure_time': flight.departure_time.isoformat(),
            'arrival_time': flight.arrival_time.isoformat(),
            'aircraft_model': flight.aircraft_model,
            'seat_capacity': flight.seat_capacity
        }, True, None
    except IntegrityError:
        db.session.rollback()
        logger.error(f"Помилка створення рейсу: Номер рейсу {flight_number} уже існує")
        return {}, False, "Номер рейсу вже існує"
    except Exception as e:
        db.session.rollback()
        logger.error(f"Помилка створення рейсу: {e}")
        return {}, False, "Не вдалося створити рейс"

def create_flight_fare(flight_id, name, base_price, base_currency, seat_limit):
    """
    Створює новий тариф для рейсу.
    
    Args:
        flight_id (int): ID рейсу
        name (str): Назва тарифу
        base_price (float): Базова ціна
        base_currency (str): Базова валюта
        seat_limit (int): Ліміт місць
    
    Returns:
        tuple: (fare: dict, success: bool, error_message: str)
    """
    try:
        if not all([flight_id, name, base_price, base_currency, seat_limit]):
            return {}, False, "Заповніть усі поля"
        flight = Flight.query.get(flight_id)
        if not flight:
            return {}, False, "Рейс не знайдено"
        if base_price <= 0:
            return {}, False, "Ціна має бути більше 0"
        if seat_limit <= 0:
            return {}, False, "Ліміт місць має бути більше 0"
        # Перевірка суми seat_limit
        current_seat_limit_sum = sum(fare.seat_limit for fare in FlightFare.query.filter_by(flight_id=flight_id).all())
        if current_seat_limit_sum + seat_limit > flight.seat_capacity:
            return {}, False, f"Сума лімітів місць ({current_seat_limit_sum + seat_limit}) перевищує місткість літака ({flight.seat_capacity})"
        fare = FlightFare(
            flight_id=flight_id,
            name=name.strip(),
            base_price=float(base_price),
            base_currency=base_currency.strip(),
            seat_limit=seat_limit,
            seats_sold=0
        )
        db.session.add(fare)
        db.session.commit()
        logger.info(f"Створено тариф {name} для рейсу {flight_id}")
        return {
            'id': fare.id,
            'flight_id': fare.flight_id,
            'name': fare.name,
            'base_price': float(fare.base_price),
            'base_currency': fare.base_currency,
            'seat_limit': fare.seat_limit,
            'seats_sold': fare.seats_sold
        }, True, None
    except Exception as e:
        db.session.rollback()
        logger.error(f"Помилка створення тарифу: {e}")
        return {}, False, "Не вдалося створити тариф"

def get_all_flights():
    """
    Отримує список усіх рейсів.
    
    Returns:
        tuple: (flights_list: list, success: bool, error_message: str)
    """
    try:
        flights = Flight.query.all()
        flights_list = [
            {
                'id': flight.id,
                'flight_number': flight.flight_number,
                'origin_airport': {'id': flight.origin_airport.id, 'code': flight.origin_airport.code, 'name': flight.origin_airport.name},
                'destination_airport': {'id': flight.destination_airport.id, 'code': flight.destination_airport.code, 'name': flight.destination_airport.name},
                'departure_time': flight.departure_time.isoformat(),
                'arrival_time': flight.arrival_time.isoformat(),
                'aircraft_model': flight.aircraft_model,
                'seat_capacity': flight.seat_capacity,
                'fares': [
                    {
                        'id': fare.id,
                        'name': fare.name,
                        'base_price': float(fare.base_price),
                        'base_currency': fare.base_currency,
                        'seat_limit': fare.seat_limit,
                        'seats_sold': fare.seats_sold
                    } for fare in flight.fares
                ]
            } for flight in flights
        ]
        logger.info(f"Отримано {len(flights_list)} рейсів")
        return flights_list, True, None
    except Exception as e:
        logger.error(f"Помилка отримання рейсів: {e}")
        return [], False, "Не вдалося отримати рейси"