from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt
from models import User, Role
import bcrypt
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No input data provided'}), 400

        email = data.get('email')
        password = data.get('password')

        if not all([email, password]):
            return jsonify({'error': 'Missing email or password'}), 400

        user = User.query.filter_by(email=email).first()
        if not user or not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            logger.warning(f"Failed login attempt for email: {email}")
            return jsonify({'error': 'Invalid email or password'}), 401

        access_token = create_access_token(identity=str(user.id), additional_claims={'role': user.role.value})
        logger.info(f"Successful login for user: {email}")
        return jsonify({
            'access_token': access_token,
            'role': user.role.value,
            'name': user.name
        }), 200

    except Exception as e:
        logger.error(f"Error during login: {e}")
        return jsonify({'error': 'Login failed'}), 500