from models import Till, Role
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

def get_all_tills(user_id, role):
    """
    Получает список касс в зависимости от роли пользователя.
    
    Args:
        user_id (int): ID пользователя
        role (str): Роль пользователя
    
    Returns:
        tuple: (tills_list: list, success: bool, error_message: str)
    """
    try:
        if role == 'cashier':
            tills = Till.query.filter_by(cashier_id=user_id).all()
        else:
            tills = Till.query.all()

        tills_list = [
            {
                'id': till.id,
                'cashier_id': till.cashier_id,
                'cashier_name': till.cashier.name,
                'cashier_email': till.cashier.email,
                'opened_at': till.opened_at.isoformat(),
                'closed_at': till.closed_at.isoformat() if till.closed_at else None,
                'is_active': till.is_active,
                'total_amount': str(till.total_amount)
            } for till in tills
        ]
        logger.info(f"Retrieved {len(tills_list)} tills for user {user_id}")
        return tills_list, True, None
    except Exception as e:
        logger.error(f"Error retrieving tills: {e}")
        return [], False, "Failed to retrieve tills"

def check_open_till():
    """
    Проверяет, есть ли открытая касса в системе.
    
    Returns:
        tuple: (open_till_data: dict, is_open: bool, error_message: str)
    """
    try:
        open_till = Till.query.filter_by(is_active=True).first()
        if open_till:
            return {
                'till_id': open_till.id,
                'cashier_id': open_till.cashier_id,
                'cashier_name': open_till.cashier.name,
                'cashier_email': open_till.cashier.email,
                'opened_at': open_till.opened_at.isoformat(),
                'total_amount': str(open_till.total_amount)
            }, True, None
        return {}, False, None
    except Exception as e:
        logger.error(f"Error checking open till: {e}")
        return {}, False, "Failed to check open till"

def open_till_for_cashier(user_id):
    """
    Открывает новую кассу для кассира.
    
    Args:
        user_id (int): ID кассира
    
    Returns:
        tuple: (till_data: dict, success: bool, error_message: str)
    """
    try:
        # Проверка, нет ли уже открытых касс
        if Till.query.filter_by(is_active=True).count() > 0:
            logger.warning(f"Attempt to open till while another is active for user {user_id}")
            return {}, False, "Another till is already open"
        
        # Создаём новую кассу
        new_till = Till(
            cashier_id=user_id,
            opened_at=datetime.now(timezone.utc),
            is_active=True,
            total_amount=0.0
        )
        Till.query.session.add(new_till)
        Till.query.session.commit()
        logger.info(f"User {user_id} opened till {new_till.id}")
        
        return {
            'till_id': new_till.id,
            'cashier_id': new_till.cashier_id,
            'opened_at': new_till.opened_at.isoformat(),
            'total_amount': str(new_till.total_amount)
        }, True, None
        
    except Exception as e:
        Till.query.session.rollback()
        logger.error(f"Error opening till for user {user_id}: {e}")
        return {}, False, "Failed to open till"

def close_till_for_cashier(user_id):
    """
    Закрывает открытую кассу кассира.
    
    Args:
        user_id (int): ID кассира
    
    Returns:
        tuple: (till_data: dict, success: bool, error_message: str)
    """
    try:
        open_till = Till.query.filter_by(cashier_id=user_id, is_active=True).first()
        if not open_till:
            logger.warning(f"No open till found for user {user_id}")
            return {}, False, "No open till found for this cashier"
        
        # Закрываем кассу
        open_till.is_active = False
        open_till.closed_at = datetime.now(timezone.utc)
        Till.query.session.commit()
        logger.info(f"User {user_id} closed till {open_till.id}")
        
        return {
            'till_id': open_till.id,
            'closed_at': open_till.closed_at.isoformat()
        }, True, None
        
    except Exception as e:
        Till.query.session.rollback()
        logger.error(f"Error closing till for user {user_id}: {e}")
        return {}, False, "Failed to close till"

def get_cashier_open_till(user_id):
    """
    Получает открытую кассу кассира.
    
    Args:
        user_id (int): ID кассира
    
    Returns:
        tuple: (open_till: Till, success: bool, error_message: str)
    """
    try:
        open_till = Till.query.filter_by(cashier_id=user_id, is_active=True).first()
        if open_till:
            return open_till, True, None
        return None, False, "No open till found"
    except Exception as e:
        logger.error(f"Error getting open till for user {user_id}: {e}")
        return None, False, "Failed to get open till"