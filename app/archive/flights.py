from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash
from flask_jwt_extended import jwt_required, get_jwt
from models import Role
from services.flight_service import get_all_flights, create_flight
import logging

logger = logging.getLogger(__name__)
flights_bp = Blueprint('flights', __name__, template_folder='../templates')

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

@flights_bp.route('/web/flights', methods=['GET', 'POST'])
@jwt_required()
def manage_flights():
    claims = get_jwt()
    if claims['role'] != Role.ADMIN.value:
        flash('Тільки адміністратори можуть керувати рейсами', 'error')
        return redirect(url_for('web.dashboard'))
    
    if request.method == 'POST':
        flight_number = request.form.get('flight_number')
        departure = request.form.get('departure')
        destination = request.form.get('destination')
        departure_time = request.form.get('departure_time')
        ticket_price = request.form.get('ticket_price')

        if not all([flight_number, departure, destination, departure_time, ticket_price]):
            flash('Заповніть усі поля: номер рейсу, відправлення, призначення, час вильоту, ціна', 'error')
            return redirect(url_for('flights.manage_flights'))

        flight, success, error_msg = create_flight(
            flight_number.strip(),
            departure.strip(),
            destination.strip(),
            departure_time.strip(),
            ticket_price.strip()
        )
        if success:
            flash(f'Рейс {flight_number} успішно створено!', 'success')
        else:
            flash(f'Помилка створення рейсу: {error_msg}', 'error')
        
        return redirect(url_for('flights.manage_flights'))

    flights_list, success, error_msg = get_all_flights()
    if not success:
        flash(f'Помилка отримання списку рейсів: {error_msg}', 'error')
        return redirect(url_for('web.dashboard'))
    
    return render_template('flights/manage_flights.html', flights=flights_list)