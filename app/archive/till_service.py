from models import Till, Role
from datetime import datetime, timezone
import logging
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
import os

logger = logging.getLogger(__name__)

# Реєстрація шрифту Noto Serif
try:
    font_path = os.path.join(os.path.dirname(__file__), '..', 'fonts', 'NotoSerif-Regular.ttf')
    pdfmetrics.registerFont(TTFont('NotoSerif', font_path))
    logger.info(f"Successfully registered NotoSerif font from {font_path}")
except Exception as e:
    logger.warning(f"Failed to register NotoSerif font: {e}, falling back to Helvetica")
    pdfmetrics.registerFont(TTFont('NotoSerif', 'Helvetica'))  # Резервний шрифт (без кирилиці)

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
        return None, True, "Наразі немає відкритої каси"
    except Exception as e:
        logger.error(f"Error getting open till for user {user_id}: {e}")
        return None, False, f"Помилка отримання відкритої каси: {str(e)}"

def reopen_till_for_cashier(admin_id, till_id):
    """
    Повторно открывает старую кассу для кассира (только для администратора).
    
    Args:
        admin_id (int): ID администратора
        till_id (int): ID кассы для повторного открытия
    
    Returns:
        tuple: (till_data: dict, success: bool, error_message: str)
    """
    try:
        # Получаем кассу
        till = Till.query.get(till_id)
        if not till:
            logger.warning(f"Till {till_id} not found for admin {admin_id}")
            return {}, False, "Till not found"
        
        # Проверяем, что касса закрыта
        if till.is_active:
            logger.warning(f"Till {till_id} is already open for admin {admin_id}")
            return {}, False, "Till is already open"
        
        # Проверяем, нет ли других открытых касс у кассира
        cashier_id = till.cashier_id
        existing_open_till = Till.query.filter_by(cashier_id=cashier_id, is_active=True).first()
        if existing_open_till:
            logger.warning(f"User {cashier_id} already has an open till {existing_open_till.id}")
            return {}, False, f"Cashier already has an open till (ID: {existing_open_till.id})"
        
        # Повторно открываем кассу
        till.is_active = True
        till.closed_at = None
        Till.query.session.commit()
        logger.info(f"Admin {admin_id} reopened till {till_id} for cashier {cashier_id}")
        
        return {
            'till_id': till.id,
            'cashier_id': till.cashier_id,
            'opened_at': till.opened_at.isoformat(),
            'total_amount': str(till.total_amount)
        }, True, None
        
    except Exception as e:
        Till.query.session.rollback()
        logger.error(f"Error reopening till {till_id} for admin {admin_id}: {e}")
        return {}, False, "Failed to reopen till"

def get_tills_by_cashier(cashier_id):
    """
    Получает список всех кас для конкретного кассира.
    
    Args:
        cashier_id (int): ID кассира
    
    Returns:
        tuple: (tills_list: list, success: bool, error_message: str)
    """
    try:
        tills = Till.query.filter_by(cashier_id=cashier_id).all()
        tills_list = [
            {
                'id': till.id,
                'opened_at': till.opened_at.isoformat(),
                'closed_at': till.closed_at.isoformat() if till.closed_at else None,
                'is_active': till.is_active,
                'total_amount': str(till.total_amount)
            } for till in tills
        ]
        logger.info(f"Retrieved {len(tills_list)} tills for cashier {cashier_id}")
        return tills_list, True, None
    except Exception as e:
        logger.error(f"Error retrieving tills for cashier {cashier_id}: {e}")
        return [], False, "Failed to retrieve tills"

def generate_tills_pdf(tills):
    """
    Генерирует PDF-файл с данными о кассах.
    
    Args:
        tills (list): Список кас
    
    Returns:
        bytes: PDF-файл в байтах
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Налаштування стилю для заголовка з підтримкою кирилиці
    styles.add(ParagraphStyle(name='CustomHeading', fontName='NotoSerif', fontSize=14, leading=16))
    
    elements.append(Paragraph("Звіт про каси касира", styles['CustomHeading']))
    
    # Визначаємо ширини стовпців (загальна ширина сторінки letter = 612 пунктів)
    col_widths = [60, 120, 120, 80, 100]  # Загальна сума ~480 пунктів
    
    data = [['ID каси', 'Дата відкриття', 'Дата закриття', 'Статус', 'Загальна сума (UAH)']]
    
    for till in tills:
        data.append([
            str(till['id']),
            datetime.fromisoformat(till['opened_at']).strftime('%d.%m.%Y %H:%M'),
            datetime.fromisoformat(till['closed_at']).strftime('%d.%m.%Y %H:%M') if till['closed_at'] else '-',
            'Відкрита' if till['is_active'] else 'Закрита',
            till['total_amount']
        ])
    
    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'NotoSerif'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    
    doc.build(elements)
    logger.debug(f"Generated PDF for tills, size: {len(buffer.getvalue())} bytes")
    return buffer.getvalue()