import csv
from io import StringIO
from flask import Blueprint, jsonify, render_template, request, redirect, url_for, make_response, flash
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, get_jwt
from werkzeug import Response
from services.flight_service import get_all_flights
from services.auth_service import authenticate_user
from services.user_service import change_user_password_by_user, get_user_by_id, get_admin_dashboard_stats
from services.shift_service import get_available_cash_desks
from services.cash_desk_service import get_cash_desk_accounts, get_cash_desk_balances_by_date
from services.ticket_service import get_sold_tickets_by_criteria, get_ticket_sales_stats
from models import Shift, CashDesk, ShiftStatus, Transaction, Role, Airport, Flight
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

web_bp = Blueprint('web', __name__, template_folder='../templates')

@web_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        logger.debug("Відображення форми входу")
        return render_template('login.html')
    try:
        logger.debug(f"Отримано POST-запит на /login з Content-Type: {request.content_type}")
        data = request.form
        email = data.get('email')
        password = data.get('password')
        if not all([email, password]):
            logger.warning(f"Спроба входу з відсутніми полями: {email}")
            flash('Заповніть усі поля', 'error')
            return render_template('login.html')
        user, success, error_msg, requires_password_change = authenticate_user(email, password)
        if not success:
            logger.warning(f"Невдала спроба входу для email: {email}")
            flash('Невірна електронна пошта або пароль', 'error')
            return render_template('login.html')
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={'role': user.role.value, 'name': user.name}
        )
        logger.info(f"Успішний вхід для користувача: {email}")
        logger.debug(f"Створено access_token: {access_token}")
    
        response = make_response()
        response.set_cookie(
            'access_token',
            access_token,
            httponly=True,
            secure=False,
            samesite='Lax',
            path='/',
            max_age=1800
        )
        response.set_cookie(
            'js_access_token',
            access_token,
            httponly=False,
            secure=False,
            samesite='Lax',
            path='/',
            max_age=1800
        )
        if requires_password_change:
            logger.debug(f"Користувач {email} повинен змінити пароль")
            response.headers['Location'] = url_for('web.change_password')
        else:
            response.headers['Location'] = url_for('web.dashboard')
        return response, 302
    except Exception as e:
        logger.error(f"Помилка під час входу: {e}")
        flash('Помилка входу', 'error')
        return render_template('login.html')

@web_bp.route('/change-password', methods=['GET', 'POST'])
@jwt_required()
def change_password():
    user_id = int(get_jwt_identity())
    user, success, error_msg = get_user_by_id(user_id)
    if not success:
        flash(error_msg, 'error')
        return redirect(url_for('web.login'))
 
    if request.method == 'GET':
        return render_template('change_password.html', user_name=user.name)
 
    try:
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
     
        if not all([current_password, new_password, confirm_password]):
            flash('Заповніть усі поля', 'error')
            return render_template('change_password.html', user_name=user.name)
     
        if new_password != confirm_password:
            flash('Новий пароль і підтвердження не співпадають', 'error')
            return render_template('change_password.html', user_name=user.name)
     
        success, error_msg = change_user_password_by_user(user_id, current_password, new_password)
        if success:
            flash('Пароль успішно змінено!', 'success')
            return redirect(url_for('web.dashboard'))
        else:
            flash(f'Помилка зміни пароля: {error_msg}', 'error')
            return render_template('change_password.html', user_name=user.name)
         
    except Exception as e:
        logger.error(f"Помилка зміни пароля для користувача {user_id}: {e}")
        flash('Не вдалося змінити пароль', 'error')
        return render_template('change_password.html', user_name=user.name)

@web_bp.route('/dashboard')
@jwt_required()
def dashboard():
    current_user = get_jwt()
    user_id = int(current_user['sub'])
    role = current_user['role']
    user_name = current_user.get('name', '')
 
    user, success, error_msg = get_user_by_id(user_id)
    if not success:
        flash(error_msg, 'error')
        return redirect(url_for('web.login'))
 
    if not user.password_changed:
        flash('Будь ласка, змініть свій пароль перед продовженням', 'warning')
        return redirect(url_for('web.change_password'))
 
    if role == Role.ADMIN.value:
        stats, success, error_msg = get_admin_dashboard_stats()
        if not success:
            flash(f'Помилка отримання статистики: {error_msg}', 'error')
            stats = {}
        return render_template('admin_dashboard.html', user_name=user_name, user_role=role, stats=stats)
 
    elif role == Role.CASHIER.value:
        open_shift = Shift.query.filter_by(cashier_id=user_id, status=ShiftStatus.OPEN).first()
        shift_status_message = None
        available_cash_desks = []
        cash_desk_accounts = []
        transactions = []
        if open_shift:
            cash_desk = CashDesk.query.get(open_shift.cash_desk_id)
            shift_status_message = f"Зміна відкрита з {open_shift.opened_at.strftime('%d.%m.%Y %H:%M')} на касі {cash_desk.name}."
            accounts, success, error_msg = get_cash_desk_accounts(open_shift.cash_desk_id)
            if success:
                cash_desk_accounts = accounts
            else:
                shift_status_message += f" Помилка отримання рахунків: {error_msg}"
            transactions = Transaction.query.filter_by(shift_id=open_shift.id).order_by(Transaction.created_at.desc()).limit(20).all()
        else:
            cash_desks, success, error_msg = get_available_cash_desks(user.airport_id)
            if success:
                available_cash_desks = cash_desks
                shift_status_message = "Наразі немає відкритої зміни."
            else:
                shift_status_message = f"Помилка: {error_msg}"
        return render_template(
            'cashier_dashboard.html',
            user_name=user_name,
            user_role=role,
            open_shift=open_shift,
            shift_status_message=shift_status_message,
            available_cash_desks=available_cash_desks,
            cash_desk_accounts=cash_desk_accounts,
            transactions=transactions
        )
 
    elif role == Role.ACCOUNTANT.value:
        airports = Airport.query.all()
        return render_template(
            'accountant_dashboard.html',
            user_name=user_name,
            user_role=role,
            airports=airports
        )
    elif role == Role.SALES_MANAGER.value:
        airports = Airport.query.all()
        flights, success, error_msg = get_all_flights()
        
        # Додайте логування для діагностики
        logger.info(f"SALES_MANAGER dashboard: Loaded {len(airports)} airports")
        logger.info(f"SALES_MANAGER dashboard: Flights success={success}, error={error_msg}, count={len(flights) if success else 0}")
        
        if not success:
            flash(f'Помилка завантаження рейсів: {error_msg}', 'warning')
        
        return render_template(
            'sales_manager_dashboard.html',
            user_name=user_name,
            airports=airports or [],  # Дефолтний порожній список
            flights=flights or []     # Дефолтний порожній список
        )
 
    return render_template(
        'base.html',
        user_name=user_name,
        user_role=role
    )

@web_bp.route('/accountant/balances', methods=['POST'])
@jwt_required()
def accountant_balances():
    claims = get_jwt()
    if claims['role'] != Role.ACCOUNTANT.value:
        flash('Тільки бухгалтери можуть переглядати баланси', 'error')
        return redirect(url_for('web.dashboard'))

    airport_id = request.form.get('airport_id')
    cash_desk_id = request.form.get('cash_desk_id')
    date1_str = request.form.get('date1')
    date2_str = request.form.get('date2')

    if not all([airport_id, date1_str]):
        flash('Виберіть аеропорт і першу дату', 'error')
        return redirect(url_for('web.dashboard'))

    try:
        date1 = datetime.strptime(date1_str, '%Y-%m-%d').date()
        date2 = datetime.strptime(date2_str, '%Y-%m-%d').date() if date2_str else None
    except ValueError:
        flash('Некоректний формат дати', 'error')
        return redirect(url_for('web.dashboard'))

    cash_desk_id = int(cash_desk_id) if cash_desk_id else None
    balances, success, error_msg = get_cash_desk_balances_by_date(airport_id, cash_desk_id, date1, date2)
    if not success:
        flash(f'Помилка отримання балансів: {error_msg}', 'error')
        return redirect(url_for('web.dashboard'))

    airports = Airport.query.all()
    return render_template(
        'accountant_dashboard.html',
        user_name=claims.get('name', 'User'),
        airports=airports,
        balances=balances,
        date1=date1.strftime('%d.%m.%Y'),
        date2=date2.strftime('%d.%m.%Y') if date2 else None
    )

@web_bp.route('/accountant/balances/export', methods=['POST'])
@jwt_required()
def export_balances():
    claims = get_jwt()
    if claims['role'] != Role.ACCOUNTANT.value:
        return Response('Тільки бухгалтери можуть експортувати баланси', status=403)

    airport_id = request.form.get('airport_id')
    cash_desk_id = request.form.get('cash_desk_id')
    date1_str = request.form.get('date1')
    date2_str = request.form.get('date2')

    if not all([airport_id, date1_str]):
        return Response('Виберіть аеропорт і першу дату', status=400)

    try:
        date1 = datetime.strptime(date1_str, '%Y-%m-%d').date()
        date2 = datetime.strptime(date2_str, '%Y-%m-%d').date() if date2_str else None
    except ValueError:
        return Response('Некоректний формат дати', status=400)

    cash_desk_id = int(cash_desk_id) if cash_desk_id else None
    balances, success, error_msg = get_cash_desk_balances_by_date(airport_id, cash_desk_id, date1, date2)
    if not success:
        return Response(f'Помилка отримання балансів: {error_msg}', status=500)

    # Створюємо CSV
    output = StringIO()
    writer = csv.writer(output)
    headers = ['Каса', 'Валюта', f'Баланс на {date1.strftime("%d.%m.%Y")}']
    if date2:
        headers.extend([f'Баланс на {date2.strftime("%d.%m.%Y")}', 'Різниця'])
    writer.writerow(headers)

    for balance in balances:
        row = [
            balance['cash_desk_name'],
            balance['currency_code'],
            f"{balance['balance_date1']:.2f}"
        ]
        if date2:
            row.extend([
                f"{balance['balance_date2']:.2f}" if balance['balance_date2'] is not None else 'Н/Д',
                f"{balance['difference']:.2f}" if balance['difference'] is not None else 'Н/Д'
            ])
        writer.writerow(row)

    output.seek(0)
    filename = f"balances_{date1.strftime('%Y%m%d')}{'_to_' + date2.strftime('%Y%m%d') if date2 else ''}.csv"
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


@web_bp.route('/sales_manager/tickets', methods=['POST'])
@jwt_required()
def sales_manager_tickets():
    claims = get_jwt()
    if claims['role'] != Role.SALES_MANAGER.value:
        flash('Тільки менеджери з продажів можуть переглядати статистику квитків', 'error')
        return redirect(url_for('web.dashboard'))

    airport_id = request.form.get('airport_id')
    flight_id = request.form.get('flight_id')

    if not all([airport_id, flight_id]):
        flash('Виберіть аеропорт і рейс', 'error')
        return redirect(url_for('web.dashboard'))

    criteria = {'airport_id': int(airport_id), 'flight_id': int(flight_id)}
    
    # Отримання списку квитків
    tickets, success, error_msg = get_sold_tickets_by_criteria(criteria)
    if not success:
        flash(f'Помилка отримання квитків: {error_msg}', 'error')
        return redirect(url_for('web.dashboard'))

    # Отримання статистики
    stats, stats_success, stats_error_msg = get_ticket_sales_stats(criteria)
    if not stats_success:
        flash(f'Помилка отримання статистики: {stats_error_msg}', 'error')
        stats = {}

    airports = Airport.query.all()
    flights, _, _ = get_all_flights()
    flight = next((f for f in flights if f['id'] == int(flight_id)), None)
    filter_info = f"{flight['flight_number']} ({flight['origin_airport']['code']} → {flight['destination_airport']['code']})" if flight else None

    return render_template(
        'sales_manager_dashboard.html',
        user_name=claims.get('name', 'User'),
        airports=airports,
        flights=flights,
        tickets=tickets,
        stats=stats,
        filter_info=filter_info
    )

@web_bp.route('/sales_manager/tickets/export', methods=['POST'])
@jwt_required()
def sales_manager_tickets_export():
    claims = get_jwt()
    if claims['role'] != Role.SALES_MANAGER.value:
        return Response('Тільки менеджери з продажів можуть експортувати статистику', status=403)

    airport_id = request.form.get('airport_id')
    flight_id = request.form.get('flight_id')

    if not all([airport_id, flight_id]):
        return Response('Виберіть аеропорт і рейс', status=400)

    criteria = {'airport_id': int(airport_id), 'flight_id': int(flight_id)}
    stats, success, error_msg = get_ticket_sales_stats(criteria)
    if not success:
        return Response(f'Помилка отримання статистики: {error_msg}', status=500)

    # Створюємо CSV
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Метрика', 'Значення'])
    writer.writerow(['Загальна кількість квитків', stats['total_tickets']])
    writer.writerow(['Загальна сума (USD)', f"{stats['total_amount_usd']:.2f}"])
    
    writer.writerow([])
    writer.writerow(['Розподіл за тарифами'])
    writer.writerow(['Тариф', 'Кількість квитків', 'Сума (USD)'])
    for fare_name, data in stats['fare_breakdown'].items():
        writer.writerow([fare_name, data['count'], f"{data['amount_usd']:.2f}"])
    
    writer.writerow([])
    writer.writerow(['Продажі за днями'])
    writer.writerow(['Дата', 'Кількість квитків', 'Сума (USD)'])
    for sale in stats['daily_sales']:
        writer.writerow([sale['date'], sale['count'], f"{sale['amount_usd']:.2f}"])

    output.seek(0)
    flight = Flight.query.get(flight_id)
    if not flight:
        return Response('Рейс не знайдено', status=404)
    filename = f"ticket_stats_flight_{flight.flight_number}_{datetime.now().strftime('%Y%m%d')}.csv"
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

@web_bp.route('/sales_manager/tickets/export', methods=['POST'])
@jwt_required()
def export_ticket_stats():
    claims = get_jwt()
    if claims['role'] != Role.SALES_MANAGER.value:
        return Response('Тільки менеджери з продажів можуть експортувати статистику', status=403)

    airport_id = request.form.get('airport_id')
    flight_id = request.form.get('flight_id')

    if not all([airport_id, flight_id]):
        return Response('Виберіть аеропорт і рейс', status=400)

    criteria = {'airport_id': int(airport_id), 'flight_id': int(flight_id)}
    stats, success, error_msg = get_ticket_sales_stats(criteria)
    if not success:
        return Response(f'Помилка отримання статистики: {error_msg}', status=500)

    # Створюємо CSV
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Метрика', 'Значення'])
    writer.writerow(['Загальна кількість квитків', stats['total_tickets']])
    writer.writerow(['Загальна сума (USD)', f"{stats['total_amount_usd']:.2f}"])
    
    writer.writerow([])
    writer.writerow(['Розподіл за тарифами'])
    writer.writerow(['Тариф', 'Кількість квитків', 'Сума (USD)'])
    for fare_name, data in stats['fare_breakdown'].items():
        writer.writerow([fare_name, data['count'], f"{data['amount_usd']:.2f}"])
    
    writer.writerow([])
    writer.writerow(['Продажі за днями'])
    writer.writerow(['Дата', 'Кількість квитків', 'Сума (USD)'])
    for sale in stats['daily_sales']:
        writer.writerow([sale['date'], sale['count'], f"{sale['amount_usd']:.2f}"])

    output.seek(0)
    flight = Flight.query.get(flight_id)
    if not flight:
        return Response('Рейс не знайдено', status=404)
    filename = f"ticket_stats_flight_{flight.flight_number}_{datetime.now().strftime('%Y%m%d')}.csv"
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

@web_bp.route('/logout')
def logout():
    response = redirect(url_for('web.login'))
    response.delete_cookie('access_token')
    response.delete_cookie('js_access_token')
    logger.debug("Куки access_token та js_access_token видалено, редирект на /login")
    return response