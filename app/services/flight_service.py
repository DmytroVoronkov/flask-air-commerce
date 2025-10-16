from models import Flight
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
import logging

logger = logging.getLogger(__name__)

def get_all_flights():
    """
    Получает список всех рейсов, которые еще не произошли.
    
    Returns:
        tuple: (flights_list: list, success: bool, error_message: str)
    """
    try:
        current_time = datetime.now(timezone.utc)
        flights = Flight.query.filter(Flight.departure_time > current_time).all()
        flights_list = [
            {
                'id': flight.id,
                'flight_number': flight.flight_number,
                'departure': flight.departure,
                'destination': flight.destination,
                'departure_time': flight.departure_time.isoformat(),
                'ticket_price': str(flight.ticket_price),
                'created_at': flight.created_at.isoformat()
            } for flight in flights
        ]
        logger.info(f"Retrieved {len(flights_list)} upcoming flights")
        return flights_list, True, None
    except Exception as e:
        logger.error(f"Error retrieving flights: {e}")
        return [], False, "Failed to retrieve flights"

def get_flight_by_id(flight_id):
    """
    Получает рейс по ID.
    
    Args:
        flight_id (int): ID рейса
    
    Returns:
        tuple: (flight: Flight, success: bool, error_message: str)
    """
    try:
        flight = Flight.query.get(flight_id)
        if not flight:
            return None, False, "Flight not found"
        return flight, True, None
    except Exception as e:
        logger.error(f"Error getting flight {flight_id}: {e}")
        return None, False, "Failed to get flight"

def create_flight(flight_number, departure, destination, departure_time, ticket_price):
    """
    Створює новий рейс.
    
    Args:
        flight_number (str): Номер рейсу
        departure (str): Місто відправлення
        destination (str): Місто призначення
        departure_time (str): Час вильоту у форматі ISO
        ticket_price (float): Ціна квитка
    
    Returns:
        tuple: (flight: dict, success: bool, error_message: str)
    """
    try:
        # Перевірка валідності часу вильоту
        try:
            departure_time_dt = datetime.fromisoformat(departure_time.replace('Z', '+00:00'))
        except ValueError:
            return {}, False, "Невірний формат часу вильоту. Використовуйте формат ISO (наприклад, 2025-10-15T14:00:00Z)"

        # Перевірка валідності ціни
        try:
            ticket_price = float(ticket_price)
            if ticket_price <= 0:
                return {}, False, "Ціна квитка має бути більшою за 0"
        except ValueError:
            return {}, False, "Ціна квитка має бути числом"

        # Створення рейсу
        new_flight = Flight(
            flight_number=flight_number.strip(),
            departure=departure.strip(),
            destination=destination.strip(),
            departure_time=departure_time_dt,
            ticket_price=ticket_price,
            created_at=datetime.now(timezone.utc)
        )
        
        Flight.query.session.add(new_flight)
        Flight.query.session.commit()
        
        logger.info(f"Створено рейс: {flight_number}")
        return {
            'id': new_flight.id,
            'flight_number': new_flight.flight_number,
            'departure': new_flight.departure,
            'destination': new_flight.destination,
            'departure_time': new_flight.departure_time.isoformat(),
            'ticket_price': str(new_flight.ticket_price),
            'created_at': new_flight.created_at.isoformat()
        }, True, None
        
    except IntegrityError:
        Flight.query.session.rollback()
        logger.error(f"Помилка створення рейсу: Номер рейсу {flight_number} вже існує")
        return {}, False, "Номер рейсу вже існує"
    except Exception as e:
        Flight.query.session.rollback()
        logger.error(f"Помилка створення рейсу: {e}")
        return {}, False, "Не вдалося створити рейс"