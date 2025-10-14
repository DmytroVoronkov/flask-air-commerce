from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from models import Flight
import logging

logger = logging.getLogger(__name__)
flights_bp = Blueprint('flights', __name__)

@flights_bp.route('/flights', methods=['GET'])
@jwt_required()
def flights():
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
        logger.info("Retrieved flights list")
        return jsonify(flights_list)
    except Exception as e:
        logger.error(f"Error retrieving flights: {e}")
        return jsonify({'error': 'Failed to retrieve flights'}), 500