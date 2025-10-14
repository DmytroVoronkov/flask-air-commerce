from flask import Blueprint, request, jsonify
from models import User, Role
from sqlalchemy.exc import IntegrityError
import bcrypt
import logging

logger = logging.getLogger(__name__)
users_bp = Blueprint('users', __name__)

@users_bp.route('/users', methods=['GET', 'POST'])
def users():
    if request.method == 'GET':
        try:
            users = User.query.all()
            users_list = [
                {
                    'id': user.id,
                    'name': user.name,
                    'email': user.email,
                    'role': user.role.value,
                    'created_at': user.created_at.isoformat()
                } for user in users
            ]
            logger.info("Retrieved user list")
            return jsonify(users_list)
        except Exception as e:
            logger.error(f"Error retrieving users: {e}")
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

            if role not in [r.value for r in Role]:
                return jsonify({'error': f"Invalid role. Must be one of: {[r.value for r in Role]}"}), 400

            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            user = User(
                name=name,
                email=email,
                password_hash=password_hash,
                role=Role[role.upper()]
            )

            User.query.session.add(user)
            User.query.session.commit()
            logger.info(f"Created user: {email}")
            return jsonify({
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'role': user.role.value,
                'created_at': user.created_at.isoformat()
            }), 201

        except IntegrityError:
            User.query.session.rollback()
            logger.error(f"Error creating user: Email {email} already exists")
            return jsonify({'error': 'Email already exists'}), 400
        except Exception as e:
            User.query.session.rollback()
            logger.error(f"Error creating user: {e}")
            return jsonify({'error': 'Failed to create user'}), 500