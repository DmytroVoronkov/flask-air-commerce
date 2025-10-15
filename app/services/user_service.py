from models import User, Role
from sqlalchemy.exc import IntegrityError
import bcrypt
import logging

logger = logging.getLogger(__name__)

def create_user(name, email, password, role_name):
    """
    Створює нового користувача.
    
    Args:
        name (str): Ім'я користувача
        email (str): Електронна пошта користувача
        password (str): Пароль користувача
        role_name (str): Роль користувача (cashier, admin, accountant)
    
    Returns:
        tuple: (user: User, success: bool, error_message: str)
    """
    try:
        # Перевірка валідності ролі
        valid_roles = [r.value for r in Role]
        if role_name not in valid_roles:
            return None, False, f"Невірна роль. Має бути одна з: {valid_roles}"
        
        # Хешування пароля
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Створення користувача
        user = User(
            name=name,
            email=email,
            password_hash=password_hash,
            role=Role[role_name.upper()]
        )
        
        User.query.session.add(user)
        User.query.session.commit()
        
        logger.info(f"Створено користувача: {email}")
        return user, True, None
        
    except IntegrityError:
        User.query.session.rollback()
        logger.error(f"Помилка створення користувача: Електронна пошта {email} вже існує")
        return None, False, "Електронна пошта вже існує"
    except Exception as e:
        User.query.session.rollback()
        logger.error(f"Помилка створення користувача: {e}")
        return None, False, "Не вдалося створити користувача"

def get_all_users():
    """
    Отримує список всіх користувачів.
    
    Returns:
        tuple: (users_list: list, success: bool, error_message: str)
    """
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
        logger.info(f"Отримано {len(users_list)} користувачів")
        return users_list, True, None
    except Exception as e:
        logger.error(f"Помилка отримання користувачів: {e}")
        return [], False, "Не вдалося отримати користувачів"

def change_user_password(user_id, new_password, admin_id):
    """
    Змінює пароль користувача (тільки для адміністратора).
    
    Args:
        user_id (int): ID користувача, чий пароль змінюється
        new_password (str): Новий пароль
        admin_id (int): ID адміністратора, який виконує дію
    
    Returns:
        tuple: (success: bool, error_message: str)
    """
    try:
        # Отримуємо користувача
        user = User.query.get(user_id)
        if not user:
            logger.warning(f"Користувача {user_id} не знайдено для адміністратора {admin_id}")
            return False, "Користувача не знайдено"
        
        # Перевіряємо, що новий пароль не порожній
        if not new_password or len(new_password) < 6:
            logger.warning(f"Невірна довжина пароля для користувача {user_id} від адміністратора {admin_id}")
            return False, "Пароль має містити принаймні 6 символів"
        
        # Хешуємо новий пароль
        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Оновлюємо пароль
        user.password_hash = password_hash
        User.query.session.commit()
        
        logger.info(f"Адміністратор {admin_id} змінив пароль для користувача {user.email} (ID: {user_id})")
        return True, None
        
    except Exception as e:
        User.query.session.rollback()
        logger.error(f"Помилка зміни пароля для користувача {user_id} адміністратором {admin_id}: {e}")
        return False, "Не вдалося змінити пароль"

def get_user_by_id(user_id):
    """
    Отримує користувача за ID.
    
    Args:
        user_id (int): ID користувача
    
    Returns:
        tuple: (user: User, success: bool, error_message: str)
    """
    try:
        user = User.query.get(user_id)
        if not user:
            logger.warning(f"Користувача {user_id} не знайдено")
            return None, False, "Користувача не знайдено"
        return user, True, None
    except Exception as e:
        logger.error(f"Помилка отримання користувача {user_id}: {e}")
        return None, False, "Не вдалося отримати користувача"