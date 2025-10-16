from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, send_file
from flask_jwt_extended import jwt_required, get_jwt
from models import Role
from services.ticket_service import sell_ticket, get_tickets_for_current_till, get_tickets_by_flight, get_tickets_by_till, generate_tickets_pdf
from services.flight_service import get_all_flights
from services.till_service import get_all_tills
import logging
from io import BytesIO

logger = logging.getLogger(__name__)
tickets_bp = Blueprint('tickets', __name__)

@tickets_bp.route('/tickets', methods=['POST'])
@jwt_required()
def sell_ticket_route():
    try:
        claims = get_jwt()
        user_id = int(claims['sub'])
        role = claims['role']
        logger.info(f"User {user_id} with role {role} attempting to sell a ticket")

        # Проверка роли
        if role != Role.CASHIER.value:
            logger.warning(f"User {user_id} with role {role} attempted to sell a ticket")
            return jsonify({'error': 'Only cashiers can sell tickets'}), 403

        # Получаем данные из запроса
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No input data provided'}), 400

        flight_id = data.get('flight_id')
        passenger_name = data.get('passenger_name')
        passenger_passport = data.get('passenger_passport')

        if not all([flight_id, passenger_name, passenger_passport]):
            return jsonify({'error': 'Missing required fields: flight_id, passenger_name, passenger_passport'}), 400

        # Используем сервис для продажи билета
        ticket_data, success, error_msg = sell_ticket(
            user_id, flight_id, passenger_name, passenger_passport
        )
        if success:
            return jsonify({
                'message': 'Ticket sold successfully',
                **ticket_data
            }), 201
        else:
            return jsonify({'error': error_msg}), 400
            
    except Exception as e:
        logger.error(f"Unexpected error selling ticket: {e}")
        return jsonify({'error': 'Failed to sell ticket'}), 500

@tickets_bp.route('/tickets', methods=['GET'])
@jwt_required()
def get_tickets():
    try:
        claims = get_jwt()
        user_id = int(claims['sub'])
        role = claims['role']
        logger.info(f"User {user_id} with role {role} requesting tickets")

        # Проверка роли
        if role != Role.CASHIER.value:
            logger.warning(f"User {user_id} with role {role} attempted to view tickets")
            return jsonify({'error': 'Only cashiers can view tickets'}), 403

        # Используем сервис для получения билетов
        tickets_data, success, error_msg = get_tickets_for_current_till(user_id)
        if success:
            return jsonify({
                'success': True,
                **tickets_data
            }), 200
        else:
            return jsonify({
                'error': error_msg,
                'tickets': tickets_data.get('tickets', []),
                'total_amount': tickets_data.get('total_amount', '0.00')
            }), 400
            
    except Exception as e:
        logger.error(f"Unexpected error retrieving tickets: {e}")
        return jsonify({
            'error': 'Failed to retrieve tickets',
            'tickets': [],
            'total_amount': '0.00'
        }), 500

@tickets_bp.route('/web/sell-ticket', methods=['GET', 'POST'])
@jwt_required()
def sell_ticket_web():
    claims = get_jwt()
    if claims['role'] != 'cashier':
        flash('Тільки касири можуть продавати квитки', 'error')
        return redirect(url_for('web.dashboard'))
    
    if request.method == 'POST':
        user_id = int(claims['sub'])
        flight_id = request.form.get('flight_id')
        passenger_name = request.form.get('passenger_name')
        passenger_passport = request.form.get('passenger_passport')

        if not all([flight_id, passenger_name, passenger_passport]):
            flash('Заповніть усі поля: рейс, ім’я пасажира, номер паспорта', 'error')
            return redirect(url_for('tickets.sell_ticket_web'))

        # Используем сервис для продажи билета
        ticket_data, success, error_msg = sell_ticket(
            user_id, int(flight_id), passenger_name.strip(), passenger_passport.strip()
        )
        
        if success:
            flash('Квиток успішно продано!', 'success')
        else:
            flash(f'Помилка продажу квитка: {error_msg}', 'error')
        
        return redirect(url_for('web.dashboard'))
    
    # GET: Отображаем форму для продажи билета
    flights, success, error_msg = get_all_flights()
    if not success:
        flash(f'Помилка отримання списку рейсів: {error_msg}', 'error')
        return redirect(url_for('web.dashboard'))
    
    return render_template('tickets/sell_ticket.html', flights=flights)

@tickets_bp.route('/web/tickets', methods=['GET'])
@jwt_required()
def view_tickets_web():
    claims = get_jwt()
    if claims['role'] != 'cashier':
        flash('Тільки касири можуть переглядати квитки', 'error')
        return redirect(url_for('web.dashboard'))
    
    user_id = int(claims['sub'])
    tickets_data, success, error_msg = get_tickets_for_current_till(user_id)
    
    if not success:
        flash(f'Помилка отримання квитків: {error_msg}', 'error')
        return redirect(url_for('web.dashboard'))
    
    return render_template('tickets/view_tickets.html', tickets_data=tickets_data)

@tickets_bp.route('/web/accountant/tickets-by-flight', methods=['GET'])
@jwt_required()
def tickets_by_flight():
    claims = get_jwt()
    if claims['role'] != 'accountant':
        flash('Тільки бухгалтери можуть переглядати квитки за рейсом', 'error')
        return redirect(url_for('web.dashboard'))
    
    flights, success, error_msg = get_all_flights()
    if not success:
        flash(f'Помилка отримання списку рейсів: {error_msg}', 'error')
        return redirect(url_for('web.dashboard'))
    
    selected_flight_id = request.args.get('flight_id')
    tickets_data = None
    if selected_flight_id:
        tickets_data, success, error_msg = get_tickets_by_flight(int(selected_flight_id))
        if not success:
            flash(f'Помилка отримання квитків: {error_msg}', 'error')
            tickets_data = None
    
    return render_template('tickets/tickets_by_flight.html', flights=flights, selected_flight_id=selected_flight_id, tickets_data=tickets_data)

@tickets_bp.route('/web/accountant/tickets-by-till', methods=['GET'])
@jwt_required()
def tickets_by_till():
    claims = get_jwt()
    if claims['role'] != 'accountant':
        flash('Тільки бухгалтери можуть переглядати квитки за касою', 'error')
        return redirect(url_for('web.dashboard'))
    
    tills, success, error_msg = get_all_tills(claims['sub'], claims['role'])
    if not success:
        flash(f'Помилка отримання списку кас: {error_msg}', 'error')
        return redirect(url_for('web.dashboard'))
    
    selected_till_id = request.args.get('till_id')
    tickets_data = None
    if selected_till_id:
        tickets_data, success, error_msg = get_tickets_by_till(int(selected_till_id))
        if not success:
            flash(f'Помилка отримання квитків: {error_msg}', 'error')
            tickets_data = None
    
    return render_template('tickets/tickets_by_till.html', tills=tills, selected_till_id=selected_till_id, tickets_data=tickets_data)

@tickets_bp.route('/web/accountant/download-tickets-by-flight-pdf/<int:flight_id>', methods=['GET'])
@jwt_required()
def download_tickets_by_flight_pdf(flight_id):
    claims = get_jwt()
    if claims['role'] != 'accountant':
        flash('Тільки бухгалтери можуть завантажувати звіти', 'error')
        return redirect(url_for('web.dashboard'))
    
    tickets_data, success, error_msg = get_tickets_by_flight(flight_id)
    if not success:
        flash(f'Помилка отримання квитків: {error_msg}', 'error')
        return redirect(url_for('tickets.tickets_by_flight'))
    
    pdf = generate_tickets_pdf(tickets_data)
    return send_file(BytesIO(pdf), as_attachment=True, attachment_filename='tickets_by_flight.pdf', mimetype='application/pdf')

@tickets_bp.route('/web/accountant/download-tickets-by-till-pdf/<int:till_id>', methods=['GET'])
@jwt_required()
def download_tickets_by_till_pdf(till_id):
    claims = get_jwt()
    if claims['role'] != 'accountant':
        flash('Тільки бухгалтери можуть завантажувати звіти', 'error')
        return redirect(url_for('web.dashboard'))
    
    tickets_data, success, error_msg = get_tickets_by_till(till_id)
    if not success:
        flash(f'Помилка отримання квитків: {error_msg}', 'error')
        return redirect(url_for('tickets.tickets_by_till'))
    
    pdf = generate_tickets_pdf(tickets_data)
    return send_file(BytesIO(pdf), as_attachment=True, attachment_filename='tickets_by_till.pdf', mimetype='application/pdf')