from models import User, Role
from sqlalchemy.exc import IntegrityError
import bcrypt
import logging

logger = logging.getLogger(__name__)

def create_user(name, email, password, role_name):
    """
    Создаёт нового пользователя.
    
    Args:
        name (str): Имя пользователя
        email (str): Email пользователя
        password (str): Пароль пользователя
        role_name (str): Роль пользователя (cashier, admin, accountant)
    
    Returns:
        tuple: (user: User, success: bool, error_message: str)
    """
    try:
        # Проверка валидности роли
        valid_roles = [r.value for r in Role]
        if role_name not in valid_roles:
            return None, False, f"Invalid role. Must be one of: {valid_roles}"
        
        # Хэширование пароля
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Создание пользователя
        user = User(
            name=name,
            email=email,
            password_hash=password_hash,
            role=Role[role_name.upper()]
        )
        
        User.query.session.add(user)
        User.query.session.commit()
        
        logger.info(f"Created user: {email}")
        return user, True, None
        
    except IntegrityError:
        User.query.session.rollback()
        logger.error(f"Email {email} already exists")
        return None, False, "Email already exists"
    except Exception as e:
        User.query.session.rollback()
        logger.error(f"Error creating user: {e}")
        return None, False, "Failed to create user"

def get_all_users():
    """
    Получает список всех пользователей.
    
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
        logger.info(f"Retrieved {len(users_list)} users")
        return users_list, True, None
    except Exception as e:
        logger.error(f"Error retrieving users: {e}")
        return [], False, "Failed to retrieve users"

def change_user_password(user_id, new_password, admin_id):
    """
    Меняет пароль пользователя (только для администратора).
    
    Args:
        user_id (int): ID пользователя, чей пароль меняется
        new_password (str): Новый пароль
        admin_id (int): ID администратора, выполняющего действие
    
    Returns:
        tuple: (success: bool, error_message: str)
    """
    try:
        # Получаем пользователя
        user = User.query.get(user_id)
        if not user:
            logger.warning(f"User {user_id} not found for admin {admin_id}")
            return False, "User not found"
        
        # Проверяем, что новый пароль не пустой
        if not new_password or len(new_password) < 6:
            logger.warning(f"Invalid password length for user {user_id} by admin {admin_id}")
            return False, "Password must be at least 6 characters long"
        
        # Хэшируем новый пароль
        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Обновляем пароль
        user.password_hash = password_hash
        User.query.session.commit()
        
        logger.info(f"Admin {admin_id} changed password for user {user.email} (ID: {user_id})")
        return True, None
        
    except Exception as e:
        User.query.session.rollback()
        logger.error(f"Error changing password for user {user_id} by admin {admin_id}: {e}")
        return False, "Failed to change password"