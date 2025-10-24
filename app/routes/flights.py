from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_jwt_extended import jwt_required, get_jwt
from models import Role, Airport, Flight
from services.flight_service import create_flight, create_flight_fare, get_all_flights
import logging

logger = logging.getLogger(__name__)

flights_bp = Blueprint('flights', __name__, template_folder='../templates')

@flights_bp.route('/flights', methods=['GET', 'POST'])
@jwt_required()
def flights():
    claims = get_jwt()
    if claims['role'] != Role.ADMIN.value:
        return jsonify({'error': 'Only admins can manage flights'}), 403
    
    if request.method == 'GET':
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
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No input data provided'}), 400
            flight_number = data.get('flight_number')
            origin_airport_id = data.get('origin_airport_id')
            destination_airport_id = data.get('destination_airport_id')
            departure_time = data.get('departure_time')
            arrival_time = data.get('arrival_time')
            aircraft_model = data.get('aircraft_model')
            seat_capacity = data.get('seat_capacity')
            if not all([flight_number, origin_airport_id, destination_airport_id, departure_time, arrival_time, aircraft_model, seat_capacity]):
                return jsonify({'error': 'Missing required fields'}), 400
            flight, success, error_msg = create_flight(
                flight_number,
                int(origin_airport_id),
                int(destination_airport_id),
                departure_time,
                arrival_time,
                aircraft_model,
                int(seat_capacity)
            )
            if success:
                return jsonify(flight), 201
            else:
                return jsonify({'error': error_msg}), 400
        except Exception as e:
            logger.error(f"Unexpected error creating flight: {e}")
            return jsonify({'error': 'Failed to create flight'}), 500

@flights_bp.route('/flights/<int:flight_id>/fares', methods=['POST'])
@jwt_required()
def create_fare(flight_id):
    claims = get_jwt()
    if claims['role'] != Role.ADMIN.value:
        return jsonify({'error': 'Only admins can manage fares'}), 403
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No input data provided'}), 400
        name = data.get('name')
        base_price = data.get('base_price')
        base_currency = data.get('base_currency')
        seat_limit = data.get('seat_limit')
        if not all([name, base_price, base_currency, seat_limit]):
            return jsonify({'error': 'Missing required fields'}), 400
        fare, success, error_msg = create_flight_fare(
            flight_id,
            name,
            float(base_price),
            base_currency,
            int(seat_limit)
        )
        if success:
            return jsonify(fare), 201
        else:
            return jsonify({'error': error_msg}), 400
    except Exception as e:
        logger.error(f"Unexpected error creating fare: {e}")
        return jsonify({'error': 'Failed to create fare'}), 500

@flights_bp.route('/web/flights', methods=['GET', 'POST'])
@jwt_required()
def manage_flights():
    claims = get_jwt()
    if claims['role'] != Role.ADMIN.value:
        flash('Тільки адміністратори можуть керувати рейсами', 'error')
        return redirect(url_for('web.dashboard'))
    
    if request.method == 'POST':
        flight_number = request.form.get('flight_number')
        origin_airport_id = request.form.get('origin_airport_id')
        destination_airport_id = request.form.get('destination_airport_id')
        departure_time = request.form.get('departure_time')
        arrival_time = request.form.get('arrival_time')
        aircraft_model = request.form.get('aircraft_model')
        seat_capacity = request.form.get('seat_capacity')
        if not all([flight_number, origin_airport_id, destination_airport_id, departure_time, arrival_time, aircraft_model, seat_capacity]):
            flash('Заповніть усі поля', 'error')
            return redirect(url_for('flights.manage_flights'))
        flight, success, error_msg = create_flight(
            flight_number,
            int(origin_airport_id),
            int(destination_airport_id),
            departure_time,
            arrival_time,
            aircraft_model,
            int(seat_capacity)
        )
        if success:
            flash(f'Рейс {flight_number} успішно створено!', 'success')
        else:
            flash(f'Помилка створення рейсу: {error_msg}', 'error')
        return redirect(url_for('flights.manage_flights'))
    
    flights_list, success, error_msg = get_all_flights()
    airports = Airport.query.all()
    if not success:
        flash(f'Помилка отримання списку рейсів: {error_msg}', 'error')
        return redirect(url_for('web.dashboard'))
    
    return render_template('flights/manage_flights.html', flights=flights_list, airports=airports)

@flights_bp.route('/web/flights/<int:flight_id>/fares', methods=['GET', 'POST'])
@jwt_required()
def add_flight_fare(flight_id):
    claims = get_jwt()
    if claims['role'] != Role.ADMIN.value:
        flash('Тільки адміністратори можуть керувати тарифами', 'error')
        return redirect(url_for('flights.manage_flights'))
    
    flight = Flight.query.get(flight_id)
    if not flight:
        flash('Рейс не знайдено', 'error')
        return redirect(url_for('flights.manage_flights'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        base_price = request.form.get('base_price')
        base_currency = request.form.get('base_currency')
        seat_limit = request.form.get('seat_limit')
        if not all([name, base_price, base_currency, seat_limit]):
            flash('Заповніть усі поля', 'error')
            return redirect(url_for('flights.add_flight_fare', flight_id=flight_id))
        
        fare, success, error_msg = create_flight_fare(
            flight_id,
            name,
            float(base_price),
            base_currency,
            int(seat_limit)
        )
        if success:
            flash(f'Тариф {name} успішно створено!', 'success')
        else:
            flash(f'Помилка створення тарифу: {error_msg}', 'error')
        return redirect(url_for('flights.add_flight_fare', flight_id=flight_id))
    
    flights_list, success, error_msg = get_all_flights()
    flight_data = next((f for f in flights_list if f['id'] == flight_id), None)
    if not flight_data:
        flash('Рейс не знайдено', 'error')
        return redirect(url_for('flights.manage_flights'))
    
    return render_template('flights/add_flight_fare.html', flight=flight_data)

@flights_bp.route('/flights/by_airport/<int:airport_id>', methods=['GET'])
@jwt_required()
def get_flights_by_airport(airport_id):
    claims = get_jwt()
    logger.debug(f"User claims: {claims}")
    if claims['role'] != Role.SALES_MANAGER.value:
        logger.warning(f"Access denied for user with role {claims['role']}")
        return jsonify({'error': 'Тільки менеджери з продажів можуть отримувати рейси'}), 403
    try:
        flights = Flight.query.filter_by(origin_airport_id=airport_id).all()
        flights_list = [
            {
                'id': flight.id,
                'flight_number': flight.flight_number,
                'origin_airport': {'code': flight.origin_airport.code},
                'destination_airport': {'code': flight.destination_airport.code}
            } for flight in flights
        ]
        logger.info(f"Отримано {len(flights_list)} рейсів для аеропорту {airport_id}")
        return jsonify(flights_list), 200
    except Exception as e:
        logger.error(f"Помилка отримання рейсів для аеропорту {airport_id}: {e}")
        return jsonify({'error': 'Не вдалося отримати рейси'}), 500