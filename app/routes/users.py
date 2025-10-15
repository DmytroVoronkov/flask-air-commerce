from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from models import Role
from services.user_service import create_user, get_all_users, change_user_password
import logging

logger = logging.getLogger(__name__)
users_bp = Blueprint('users', __name__)

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

            if not all([name, email, password, role]):
                return jsonify({'error': 'Missing required fields'}), 400

            # Используем сервис для создания пользователя
            user, success, error_msg = create_user(name, email, password, role)
            if success:
                return jsonify({
                    'id': user.id,
                    'name': user.name,
                    'email': user.email,
                    'role': user.role.value,
                    'created_at': user.created_at.isoformat()
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

        # Проверка роли
        if role != Role.ADMIN.value:
            logger.warning(f"User {admin_id} with role {role} attempted to change password for user {user_id}")
            return jsonify({'error': 'Only admins can change user passwords'}), 403

        # Получаем данные из запроса
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No input data provided'}), 400

        new_password = data.get('password')
        if not new_password:
            return jsonify({'error': 'Password is required'}), 400

        # Используем сервис для смены пароля
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