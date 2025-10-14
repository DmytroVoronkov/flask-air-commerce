from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from services.user_service import create_user, get_all_users
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