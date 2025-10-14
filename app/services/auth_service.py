from models import User
import bcrypt
import logging

logger = logging.getLogger(__name__)

def authenticate_user(email, password):
    """
    Аутентифицирует пользователя по email и паролю.
    
    Returns:
        tuple: (user: User, success: bool, error_message: str)
    """
    try:
        user = User.query.filter_by(email=email).first()
        if not user:
            logger.warning(f"Login attempt for non-existent email: {email}")
            return None, False, "User not found"
        
        if not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            logger.warning(f"Failed login attempt for email: {email}")
            return None, False, "Invalid password"
        
        logger.info(f"Successful authentication for user: {email}")
        return user, True, None
        
    except Exception as e:
        logger.error(f"Error during authentication: {e}")
        return None, False, "Authentication failed"

def get_user_by_id(user_id):
    """
    Получает пользователя по ID.
    
    Returns:
        User or None
    """
    try:
        user = User.query.get(user_id)
        if not user:
            logger.warning(f"User {user_id} not found")
            return None
        return user
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        return None