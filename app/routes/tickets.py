from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from models import Ticket, Till, Flight, Role
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)
tickets_bp = Blueprint('tickets', __name__)

@tickets_bp.route('/tickets', methods=['POST'])
@jwt_required()
def sell_ticket():
    try:
        claims = get_jwt()
        user_id = int(claims['sub'])
        role = claims['role']
        logger.info(f"User {user_id} with role {role} attempting to sell a ticket")

        if role != Role.CASHIER.value:
            logger.warning(f"User {user_id} with role {role} attempted to sell a ticket")
            return jsonify({'error': 'Only cashiers can sell tickets'}), 403

        open_till = Till.query.filter_by(cashier_id=user_id, is_active=True).first()
        if not open_till:
            logger.warning(f"No open till found for user {user_id} when selling ticket")
            return jsonify({'error': 'No open till. Please open a till first'}), 400

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No input data provided'}), 400

        flight_id = data.get('flight_id')
        passenger_name = data.get('passenger_name')
        passenger_passport = data.get('passenger_passport')

        if not all([flight_id, passenger_name, passenger_passport]):
            return jsonify({'error': 'Missing required fields: flight_id, passenger_name, passenger_passport'}), 400

        flight = Flight.query.get(flight_id)
        if not flight:
            return jsonify({'error': 'Flight not found'}), 404

        price = flight.ticket_price

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

        open_till.total_amount += price
        Ticket.query.session.commit()

        logger.info(f"User {user_id} sold ticket {new_ticket.id} for flight {flight_id}")

        return jsonify({
            'message': 'Ticket sold successfully',
            'ticket_id': new_ticket.id,
            'flight_number': flight.flight_number,
            'passenger_name': new_ticket.passenger_name,
            'price': str(new_ticket.price),
            'sold_at': new_ticket.sold_at.isoformat(),
            'till_total_amount': str(open_till.total_amount)
        }), 201

    except Exception as e:
        Ticket.query.session.rollback()
        logger.error(f"Error selling ticket for user {user_id}: {e}")
        return jsonify({'error': 'Failed to sell ticket'}), 500

@tickets_bp.route('/tickets', methods=['GET'])
@jwt_required()
def get_tickets():
    try:
        claims = get_jwt()
        user_id = int(claims['sub'])
        role = claims['role']
        logger.info(f"User {user_id} with role {role} requesting tickets")

        if role != Role.CASHIER.value:
            logger.warning(f"User {user_id} with role {role} attempted to view tickets")
            return jsonify({'error': 'Only cashiers can view tickets'}), 403

        open_till = Till.query.filter_by(cashier_id=user_id, is_active=True).first()
        if not open_till:
            logger.warning(f"No open till found for user {user_id}")
            return jsonify({
                'error': 'No open till. Please open a till first',
                'tickets': [],
                'total_amount': '0.00'
            }), 400

        tickets = Ticket.query.filter_by(
            till_id=open_till.id,
            status='sold'
        ).order_by(Ticket.sold_at.desc()).all()

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

        return jsonify({
            'success': True,
            'till_id': open_till.id,
            'tickets': tickets_list,
            'total_tickets': len(tickets_list),
            'total_amount': f"{total_sold:.2f}",
            'currency': 'UAH'
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving tickets for user {user_id}: {e}")
        return jsonify({
            'error': 'Failed to retrieve tickets',
            'tickets': [],
            'total_amount': '0.00'
        }), 500