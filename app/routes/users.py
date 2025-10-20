from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_jwt_extended import jwt_required, get_jwt
from models import Role, Airport
from services.user_service import create_user, get_all_users, change_user_password, get_user_by_id
from services.cash_desk_service import get_all_cash_desks, create_cash_desk, update_cash_desk
import logging
logger = logging.getLogger(__name__)

users_bp = Blueprint('users', __name__, template_folder='../templates')

@users_bp.route('/users', methods=['GET', 'POST'])
@jwt_required()
def users():
    if request.method == 'GET':
        try:
            users_list, success, error_msg = get_all_users()
            if success:
                return jsonify(users_list)
            else:
                logger.error(f"Error retrieving users: {error_msg}")
                return jsonify({'error': error_msg}), 500
        except Exception as e:
            logger.error(f"Unexpected error retrieving users: {e}")
            return jsonify({'error': 'Failed to retrieve users'}), 500
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No input data provided'}), 400
            name = data.get('name')
            email = data.get('email')
            password = data.get('password')
            role = data.get('role')
            airport_id = data.get('airport_id')
            if not all([name, email, password, role]):
                return jsonify({'error': 'Missing required fields'}), 400
            if role == 'cashier' and not airport_id:
                return jsonify({'error': 'Airport ID required for cashier role'}), 400
            if role != 'cashier' and airport_id:
                return jsonify({'error': 'Airport ID can only be set for cashier role'}), 400
            user, success, error_msg = create_user(name, email, password, role, airport_id)
            if success:
                return jsonify({
                    'id': user.id,
                    'name': user.name,
                    'email': user.email,
                    'role': user.role.value,
                    'created_at': user.created_at.isoformat(),
                    'password_changed': user.password_changed,
                    'airport_id': user.airport_id
                }), 201
            else:
                return jsonify({'error': error_msg}), 400
        except Exception as e:
            logger.error(f"Unexpected error creating user: {e}")
            return jsonify({'error': 'Failed to create user'}), 500

@users_bp.route('/users/<int:user_id>/password', methods=['PUT'])
@jwt_required()
def change_user_password_route(user_id):
    try:
        claims = get_jwt()
        admin_id = int(claims['sub'])
        role = claims['role']
        logger.info(f"User {admin_id} with role {role} attempting to change password for user {user_id}")
        if role != Role.ADMIN.value:
            logger.warning(f"User {admin_id} with role {role} attempted to change password for user {user_id}")
            return jsonify({'error': 'Only admins can change user passwords'}), 403
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No input data provided'}), 400
        new_password = data.get('password')
        if not new_password:
            return jsonify({'error': 'Password is required'}), 400
        success, error_msg = change_user_password(user_id, new_password, admin_id)
        if success:
            return jsonify({
                'message': 'Password changed successfully',
                'user_id': user_id
            }), 200
        else:
            return jsonify({'error': error_msg}), 400
    except Exception as e:
        logger.error(f"Unexpected error changing password for user {user_id}: {e}")
        return jsonify({'error': 'Failed to change password'}), 500

@users_bp.route('/web/users', methods=['GET', 'POST'])
@jwt_required()
def manage_users():
    claims = get_jwt()
    if claims['role'] != Role.ADMIN.value:
        flash('Тільки адміністратори можуть керувати користувачами', 'error')
        return redirect(url_for('web.dashboard'))
   
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        airport_id = request.form.get('airport_id')
        if not all([name, email, password, role]):
            flash('Заповніть усі поля: ім’я, email, пароль, роль', 'error')
            return redirect(url_for('users.manage_users'))
        if role == 'cashier' and not airport_id:
            flash('Для касира потрібно вибрати аеропорт', 'error')
            return redirect(url_for('users.manage_users'))
        if role != 'cashier' and airport_id:
            flash('Аеропорт можна вибрати лише для касира', 'error')
            return redirect(url_for('users.manage_users'))
        user, success, error_msg = create_user(
            name.strip(), 
            email.strip(), 
            password.strip(), 
            role.strip(), 
            int(airport_id) if airport_id else None
        )
        if success:
            flash(f'Користувача {name} успішно створено!', 'success')
        else:
            flash(f'Помилка створення користувача: {error_msg}', 'error')
        return redirect(url_for('users.manage_users'))
    
    users_list, success, error_msg = get_all_users()
    airports = Airport.query.all()
    if not success:
        flash(f'Помилка отримання списку користувачів: {error_msg}', 'error')
        return redirect(url_for('web.dashboard'))
   
    return render_template('users/manage_users.html', users=users_list, roles=[r.value for r in Role], airports=airports)

@users_bp.route('/web/users/<int:user_id>', methods=['GET'])
@jwt_required()
def manage_user(user_id):
    claims = get_jwt()
    if claims['role'] != Role.ADMIN.value:
        flash('Тільки адміністратори можуть керувати користувачами', 'error')
        return redirect(url_for('web.dashboard'))
   
    user, success, error_msg = get_user_by_id(user_id)
    if not success:
        flash(f'Помилка: {error_msg}', 'error')
        return redirect(url_for('users.manage_users'))
   
    return render_template('users/manage_user.html', user=user)

@users_bp.route('/web/users/<int:user_id>/change-password', methods=['POST'])
@jwt_required()
def change_user_password_web(user_id):
    logger.debug(f"Processing change_user_password_web for user_id={user_id}")
    claims = get_jwt()
    admin_id = int(claims['sub'])
    if claims['role'] != Role.ADMIN.value:
        flash('Тільки адміністратори можуть змінювати паролі', 'error')
        return redirect(url_for('users.manage_user', user_id=user_id))
   
    try:
        new_password = request.form.get('new_password')
        if not new_password:
            flash('Новий пароль не вказано', 'error')
            return redirect(url_for('users.manage_user', user_id=user_id))
       
        success, error_msg = change_user_password(user_id, new_password.strip(), admin_id)
        if success:
            flash('Пароль успішно скинуто! Користувач повинен змінити його при наступному вході.', 'success')
        else:
            flash(f'Помилка зміни пароля: {error_msg}', 'error')
       
        logger.debug(f"Redirecting to users.manage_user with user_id={user_id}")
        return redirect(url_for('users.manage_user', user_id=user_id))
   
    except Exception as e:
        logger.error(f"Помилка зміни пароля для користувача {user_id} адміністратором {admin_id}: {e}")
        flash('Не вдалося змінити пароль', 'error')
        return redirect(url_for('users.manage_user', user_id=user_id))

@users_bp.route('/web/cash-desks', methods=['GET', 'POST'])
@jwt_required()
def manage_cash_desks():
    claims = get_jwt()
    if claims['role'] != Role.ADMIN.value:
        flash('Тільки адміністратори можуть керувати касами', 'error')
        return redirect(url_for('web.dashboard'))
   
    if request.method == 'POST':
        name = request.form.get('name')
        airport_id = request.form.get('airport_id')
        is_active = request.form.get('is_active') == 'on'
        cash_desk_id = request.form.get('cash_desk_id')
        
        if not all([name, airport_id]):
            flash('Заповніть усі поля: назва, аеропорт', 'error')
            return redirect(url_for('users.manage_cash_desks'))
        
        if cash_desk_id:  # Оновлення каси
            success, error_msg = update_cash_desk(
                int(cash_desk_id),
                name.strip(),
                int(airport_id),
                is_active
            )
            if success:
                flash(f'Касу {name} успішно оновлено!', 'success')
            else:
                flash(f'Помилка оновлення каси: {error_msg}', 'error')
        else:  # Створення нової каси
            cash_desk, success, error_msg = create_cash_desk(
                name.strip(),
                int(airport_id),
                is_active
            )
            if success:
                flash(f'Касу {name} успішно створено!', 'success')
            else:
                flash(f'Помилка створення каси: {error_msg}', 'error')
        
        return redirect(url_for('users.manage_cash_desks'))
    
    cash_desks_list, success, error_msg = get_all_cash_desks()
    airports = Airport.query.all()
    if not success:
        flash(f'Помилка отримання списку кас: {error_msg}', 'error')
        return redirect(url_for('web.dashboard'))
   
    return render_template('users/manage_cash_desks.html', cash_desks=cash_desks_list, airports=airports)