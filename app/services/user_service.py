from models import User, Role, Airport, CashDesk, Shift
from sqlalchemy.exc import IntegrityError
import bcrypt
import logging
logger = logging.getLogger(__name__)

def create_user(name, email, password, role_name, airport_id=None):
    """
    Створює нового користувача.
   
    Args:
        name (str): Ім'я користувача
        email (str): Електронна пошта користувача
        password (str): Пароль користувача
        role_name (str): Роль користувача (cashier, admin, accountant)
        airport_id (int, optional): ID аеропорту для касира
   
    Returns:
        tuple: (user: User, success: bool, error_message: str)
    """
    try:
        valid_roles = [r.value for r in Role]
        if role_name not in valid_roles:
            return None, False, f"Невірна роль. Має бути одна з: {valid_roles}"
        if role_name == 'cashier' and not airport_id:
            return None, False, "Для касира потрібно вказати аеропорт"
        if role_name != 'cashier' and airport_id:
            return None, False, "Аеропорт можна вказати лише для касира"
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user = User(
            name=name,
            email=email,
            password_hash=password_hash,
            role=Role[role_name.upper()],
            password_changed=False,
            airport_id=airport_id
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
        user = User.query.get(user_id)
        if not user:
            logger.warning(f"Користувача {user_id} не знайдено для адміністратора {admin_id}")
            return False, "Користувача не знайдено"
        if not new_password or len(new_password) < 6:
            logger.warning(f"Невірна довжина пароля для користувача {user_id} від адміністратора {admin_id}")
            return False, "Пароль має містити принаймні 6 символів"
        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user.password_hash = password_hash
        user.password_changed = False
        User.query.session.commit()
        logger.info(f"Адміністратор {admin_id} змінив пароль для користувача {user.email} (ID: {user_id})")
        return True, None
    except Exception as e:
        User.query.session.rollback()
        logger.error(f"Помилка зміни пароля для користувача {user_id} адміністратором {admin_id}: {e}")
        return False, "Не вдалося змінити пароль"

def change_user_password_by_user(user_id, current_password, new_password):
    """
    Змінює пароль користувача самим користувачем.
   
    Args:
        user_id (int): ID користувача
        current_password (str): Поточний пароль
        new_password (str): Новий пароль
   
    Returns:
        tuple: (success: bool, error_message: str)
    """
    try:
        user = User.query.get(user_id)
        if not user:
            logger.warning(f"Користувача {user_id} не знайдено")
            return False, "Користувача не знайдено"
        if not bcrypt.checkpw(current_password.encode('utf-8'), user.password_hash.encode('utf-8')):
            logger.warning(f"Невірний поточний пароль для користувача {user_id}")
            return False, "Невірний поточний пароль"
        if not new_password or len(new_password) < 6:
            logger.warning(f"Невірна довжина нового пароля для користувача {user_id}")
            return False, "Новий пароль має містити принаймні 6 символів"
        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user.password_hash = password_hash
        user.password_changed = True
        User.query.session.commit()
        logger.info(f"Користувач {user.email} (ID: {user_id}) змінив свій пароль")
        return True, None
    except Exception as e:
        User.query.session.rollback()
        logger.error(f"Помилка зміни пароля користувачем {user_id}: {e}")
        return False, "Не вдалося змінити пароль"

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
                'created_at': user.created_at.isoformat(),
                'password_changed': user.password_changed,
                'airport_id': user.airport_id
            } for user in users
        ]
        logger.info(f"Отримано {len(users_list)} користувачів")
        return users_list, True, None
    except Exception as e:
        logger.error(f"Помилка отримання користувачів: {e}")
        return [], False, "Не вдалося отримати користувачів"

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
        logger.info(f"Отримано користувача {user_id}")
        return user, True, None
    except Exception as e:
        logger.error(f"Помилка отримання користувача {user_id}: {e}")
        return None, False, f"Не вдалося отримати користувача: {str(e)}"

def get_admin_dashboard_stats():
    """
    Отримує статистику для дашборду адміністратора.
   
    Returns:
        tuple: (stats: dict, success: bool, error_message: str)
    """
    try:
        stats = {
            'airport_count': Airport.query.count(),
            'active_cash_desk_count': CashDesk.query.filter_by(is_active=True).count(),
            'open_shift_count': Shift.query.filter_by(status='open').count(),
            'airports': [
                {
                    'id': airport.id,
                    'code': airport.code,
                    'name': airport.name,
                    'cash_desk_count': CashDesk.query.filter_by(airport_id=airport.id).count(),
                    'open_shift_count': Shift.query.join(CashDesk).filter(
                        CashDesk.airport_id == airport.id,
                        Shift.status == 'open'
                    ).count()
                } for airport in Airport.query.all()
            ]
        }
        logger.info("Отримано статистику для дашборду адміністратора")
        return stats, True, None
    except Exception as e:
        logger.error(f"Помилка отримання статистики для дашборду: {e}")
        return {}, False, "Не вдалося отримати статистику"