from models import Ticket, Till, Flight, Role
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

def sell_ticket(user_id, flight_id, passenger_name, passenger_passport):
    """
    Продаёт билет кассиру.
    
    Args:
        user_id (int): ID кассира
        flight_id (int): ID рейса
        passenger_name (str): Имя пассажира
        passenger_passport (str): Паспорт пассажира
    
    Returns:
        tuple: (ticket_data: dict, success: bool, error_message: str)
    """
    try:
        # Проверка открытой кассы
        open_till = Till.query.filter_by(cashier_id=user_id, is_active=True).first()
        if not open_till:
            logger.warning(f"No open till found for user {user_id} when selling ticket")
            return {}, False, "No open till. Please open a till first"
        
        # Получаем рейс и цену
        flight = Flight.query.get(flight_id)
        if not flight:
            return {}, False, "Flight not found"
        
        price = flight.ticket_price
        
        # Создаём билет
        new_ticket = Ticket(
            till_id=open_till.id,
            flight_id=flight_id,
            passenger_name=passenger_name,
            passenger_passport=passenger_passport,
            price=price,
            status='sold',
            sold_at=datetime.now(timezone.utc)
        )
        Ticket.query.session.add(new_ticket)
        
        # Обновляем total_amount в кассе
        open_till.total_amount += price
        Ticket.query.session.commit()
        
        logger.info(f"User {user_id} sold ticket {new_ticket.id} for flight {flight_id}")
        
        return {
            'ticket_id': new_ticket.id,
            'flight_number': flight.flight_number,
            'passenger_name': new_ticket.passenger_name,
            'price': str(new_ticket.price),
            'sold_at': new_ticket.sold_at.isoformat(),
            'till_total_amount': str(open_till.total_amount)
        }, True, None
        
    except Exception as e:
        Ticket.query.session.rollback()
        logger.error(f"Error selling ticket for user {user_id}: {e}")
        return {}, False, "Failed to sell ticket"

def get_tickets_for_current_till(user_id):
    """
    Получает билеты текущей открытой кассы кассира.
    
    Args:
        user_id (int): ID кассира
    
    Returns:
        tuple: (tickets_data: dict, success: bool, error_message: str)
    """
    try:
        # Проверка открытой кассы
        open_till = Till.query.filter_by(cashier_id=user_id, is_active=True).first()
        if not open_till:
            logger.warning(f"No open till found for user {user_id}")
            return {
                'tickets': [],
                'total_amount': '0.00',
                'total_tickets': 0
            }, False, "No open till. Please open a till first"
        
        # Получаем билеты только из текущей кассы
        tickets = Ticket.query.filter_by(
            till_id=open_till.id,
            status='sold'
        ).order_by(Ticket.sold_at.desc()).all()
        
        # Формируем список с деталями рейсов
        tickets_list = []
        total_sold = 0.0
        
        for ticket in tickets:
            flight = ticket.flight
            tickets_list.append({
                'id': ticket.id,
                'flight_number': flight.flight_number,
                'departure': flight.departure,
                'destination': flight.destination,
                'departure_time': flight.departure_time.isoformat(),
                'passenger_name': ticket.passenger_name,
                'passenger_passport': ticket.passenger_passport,
                'price': str(ticket.price),
                'sold_at': ticket.sold_at.isoformat()
            })
            total_sold += float(ticket.price)
        
        logger.info(f"User {user_id} retrieved {len(tickets_list)} tickets from till {open_till.id}")
        
        return {
            'till_id': open_till.id,
            'tickets': tickets_list,
            'total_tickets': len(tickets_list),
            'total_amount': f"{total_sold:.2f}",
            'currency': 'UAH'
        }, True, None
        
    except Exception as e:
        logger.error(f"Error retrieving tickets for user {user_id}: {e}")
        return {
            'tickets': [],
            'total_amount': '0.00',
            'total_tickets': 0
        }, False, "Failed to retrieve tickets"