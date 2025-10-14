import logging
from flask_jwt_extended import get_jwt
from models import Role
from flask import jsonify

logger = logging.getLogger(__name__)

def require_cashier_role():
    def decorator(f):
        def wrapped_function(*args, **kwargs):
            claims = get_jwt()
            role = claims['role']
            user_id = int(claims['sub'])
            if role != Role.CASHIER.value:
                logger.warning(f"User {user_id} with role {role} attempted to access cashier-only endpoint")
                return jsonify({'error': 'Only cashiers can access this endpoint'}), 403
            return f(*args, **kwargs)
        return wrapped_function
    return decorator