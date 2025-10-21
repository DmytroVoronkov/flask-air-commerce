from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_jwt_extended import jwt_required, get_jwt
from models import ExchangeRate, Role, Flight, FlightFare, Shift, ShiftStatus
from services.ticket_service import sell_ticket
import logging

logger = logging.getLogger(__name__)
tickets_bp = Blueprint('tickets', __name__, template_folder='../templates')

@tickets_bp.route('/web/tickets/sell', methods=['GET', 'POST'])
@jwt_required()
def sell_ticket_web():
    claims = get_jwt()
    if claims['role'] != Role.CASHIER.value:
        flash('Тільки касири можуть продавати квитки', 'error')
        return redirect(url_for('web.dashboard'))

    user_id = int(claims['sub'])
    open_shift = Shift.query.filter_by(cashier_id=user_id, status=ShiftStatus.OPEN).first()
    if not open_shift:
        flash('Відкрийте зміну перед продажем квитків', 'error')
        return redirect(url_for('web.dashboard'))

    if request.method == 'POST':
        flight_id = request.form.get('flight_id')
        flight_fare_id = request.form.get('flight_fare_id')
        passenger_name = request.form.get('passenger_name')
        seat_number = request.form.get('seat_number')
        currency_code = request.form.get('currency_code')

        if not all([flight_id, flight_fare_id, passenger_name, seat_number, currency_code]):
            flash('Заповніть усі поля', 'error')
            return redirect(url_for('tickets.sell_ticket_web'))

        ticket_data, success, error_msg = sell_ticket(
            user_id, int(flight_id), int(flight_fare_id), passenger_name, seat_number, currency_code
        )
        if success:
            flash(f'Квиток для {passenger_name} на рейс {ticket_data["flight_number"]} успішно продано!', 'success')
            return redirect(url_for('web.dashboard'))
        else:
            flash(f'Помилка продажу квитка: {error_msg}', 'error')
            return redirect(url_for('tickets.sell_ticket_web'))

    # Отримання доступних рейсів і валют
    flights = Flight.query.all()
    currencies = ['USD', 'UAH', 'EUR']  # Можна витягувати з cash_desk_accounts
    return render_template(
        'tickets/sell_ticket.html',
        flights=flights,
        currencies=currencies
    )

@tickets_bp.route('/tickets', methods=['POST'])
@jwt_required()
def sell_ticket_api():
    claims = get_jwt()
    if claims['role'] != Role.CASHIER.value:
        return jsonify({'error': 'Only cashiers can sell tickets'}), 403

    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No input data provided'}), 400

        user_id = int(claims['sub'])
        flight_id = data.get('flight_id')
        flight_fare_id = data.get('flight_fare_id')
        passenger_name = data.get('passenger_name')
        seat_number = data.get('seat_number')
        currency_code = data.get('currency_code')

        if not all([flight_id, flight_fare_id, passenger_name, seat_number, currency_code]):
            return jsonify({'error': 'Missing required fields'}), 400

        ticket_data, success, error_msg = sell_ticket(
            user_id, flight_id, flight_fare_id, passenger_name, seat_number, currency_code
        )
        if success:
            return jsonify(ticket_data), 201
        else:
            return jsonify({'error': error_msg}), 400

    except Exception as e:
        logger.error(f"Unexpected error selling ticket: {e}")
        return jsonify({'error': 'Failed to sell ticket'}), 500

@tickets_bp.route('/flights/<int:flight_id>/fares', methods=['GET'])
@jwt_required()
def get_fares_for_flight(flight_id):
    try:
        logger.debug(f"Fetching fares for flight_id: {flight_id}")
        fares = FlightFare.query.filter_by(flight_id=flight_id).all()
        fares_list = [
            {
                'id': fare.id,
                'name': fare.name,
                'base_price': float(fare.base_price),
                'base_currency': fare.base_currency,
                'seat_limit': fare.seat_limit,
                'seats_sold': fare.seats_sold
            } for fare in fares
        ]
        logger.debug(f"Fares found: {len(fares_list)}")
        return jsonify(fares_list), 200
    except Exception as e:
        logger.error(f"Error retrieving fares for flight {flight_id}: {e}")
        return jsonify({'error': 'Failed to retrieve fares'}), 500

@tickets_bp.route('/exchange_rates', methods=['GET'])
@jwt_required()
def get_exchange_rate():
    try:
        base_currency = request.args.get('base_currency')
        target_currency = request.args.get('target_currency')
        if not all([base_currency, target_currency]):
            return jsonify({'error': 'Missing base_currency or target_currency'}), 400

        exchange_rate = ExchangeRate.query.filter_by(
            base_currency=base_currency,
            target_currency=target_currency
        ).order_by(ExchangeRate.valid_at.desc()).first()

        if not exchange_rate:
            logger.warning(f"Exchange rate not found for {base_currency} -> {target_currency}")
            return jsonify({'error': 'Exchange rate not found'}), 404

        logger.debug(f"Exchange rate found: {base_currency} -> {target_currency}, rate={exchange_rate.rate}")
        return jsonify({
            'rate': float(exchange_rate.rate),
            'valid_at': exchange_rate.valid_at.isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Error retrieving exchange rate: {e}")
        return jsonify({'error': 'Failed to retrieve exchange rate'}), 500