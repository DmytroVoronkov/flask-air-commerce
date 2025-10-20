from models import User
import bcrypt
import logging

logger = logging.getLogger(__name__)

def authenticate_user(email, password):
    """
    Аутентифікує користувача за email і паролем.
   
    Returns:
        tuple: (user: User, success: bool, error_message: str, requires_password_change: bool)
    """
    try:
        user = User.query.filter_by(email=email).first()
        if not user:
            logger.warning(f"Спроба входу для неіснуючого email: {email}")
            return None, False, "Користувача не знайдено", False
       
        if not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            logger.warning(f"Невдала спроба входу для email: {email}")
            return None, False, "Невірний пароль", False
       
        logger.info(f"Успішна аутентифікація для користувача: {email}")
        return user, True, None, not user.password_changed
       
    except Exception as e:
        logger.error(f"Помилка під час аутентифікації: {e}")
        return None, False, "Помилка аутентифікації", False