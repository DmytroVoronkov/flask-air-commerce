from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from services.flight_service import get_all_flights
import logging

logger = logging.getLogger(__name__)
flights_bp = Blueprint('flights', __name__)

@flights_bp.route('/flights', methods=['GET'])
@jwt_required()
def flights():
    try:
        flights_list, success, error_msg = get_all_flights()
        if success:
            return jsonify(flights_list)
        else:
            logger.error(f"Error retrieving flights: {error_msg}")
            return jsonify({'error': error_msg}), 500
    except Exception as e:
        logger.error(f"Unexpected error retrieving flights: {e}")
        return jsonify({'error': 'Failed to retrieve flights'}), 500