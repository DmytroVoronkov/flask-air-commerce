from models import Flight
import logging

logger = logging.getLogger(__name__)

def get_all_flights():
    """
    Получает список всех рейсов.
    
    Returns:
        tuple: (flights_list: list, success: bool, error_message: str)
    """
    try:
        flights = Flight.query.all()
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
        logger.info(f"Retrieved {len(flights_list)} flights")
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