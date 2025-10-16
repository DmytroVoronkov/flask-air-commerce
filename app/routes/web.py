from flask import Blueprint, render_template, request, redirect, url_for, make_response, flash
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, get_jwt
from services.auth_service import authenticate_user
import logging

logger = logging.getLogger(__name__)
web_bp = Blueprint('web', __name__, template_folder='../templates')

@web_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        logger.debug("Відображення форми входу")
        return render_template('login.html')
    
    # POST: Обработка формы логина
    try:
        logger.debug(f"Отримано POST-запит на /login з Content-Type: {request.content_type}")
        data = request.form
        email = data.get('email')
        password = data.get('password')

        if not all([email, password]):
            logger.warning(f"Спроба входу з відсутніми полями: {email}")
            flash('Заповніть усі поля', 'error')
            return render_template('login.html')

        # Аутентификация через сервис
        user, success, error_msg = authenticate_user(email, password)
        if not success:
            logger.warning(f"Невдала спроба входу для email: {email}")
            flash('Невірна електронна пошта або пароль', 'error')
            return render_template('login.html')

        # Создаём токен и сохраняем в куки
        access_token = create_access_token(
            identity=str(user.id), 
            additional_claims={'role': user.role.value, 'name': user.name}
        )
        logger.info(f"Успішний вхід для користувача: {email}")
        logger.debug(f"Создан access_token: {access_token}")
        
        # Создаём ответ с редиректом на дашборд
        response = make_response(redirect(url_for('web.dashboard')))
        response.set_cookie(
            'access_token', 
            access_token, 
            httponly=True, 
            secure=False,  # False для локальной разработки
            samesite='Lax', 
            path='/',
            max_age=1800  # Токен живёт 30 хвилин
        )
        logger.debug("Куки access_token установлены для редиректа на /dashboard")
        return response

    except Exception as e:
        logger.error(f"Помилка під час входу: {e}")
        flash('Помилка входу', 'error')
        return render_template('login.html')

@web_bp.route('/dashboard')
@jwt_required()
def dashboard():
    from services.till_service import get_cashier_open_till  # Перенесений імпорт
    
    current_user = get_jwt()
    user_id = int(current_user['sub'])
    role = current_user['role']
    user_name = current_user.get('name', '')
    
    # Для кассира отримуємо статус каси
    open_till = None
    till_status_message = None
    
    if role == 'cashier':
        open_till, success, message = get_cashier_open_till(user_id)
        if success and open_till:
            till_status_message = f"Каса відкрита з {open_till.opened_at.strftime('%d.%m.%Y %H:%M')}. Загальна сума: {open_till.total_amount:.2f} грн"
        elif success:
            till_status_message = message  # "Наразі немає відкритої каси"
        else:
            till_status_message = message  # Помилка, наприклад, "Помилка отримання відкритої каси: ..."
    
    return render_template('dashboard.html', 
                         user_name=user_name, 
                         user_role=role,
                         role=role,
                         open_till=open_till,
                         till_status_message=till_status_message)

@web_bp.route('/logout')
def logout():
    response = redirect(url_for('web.login'))
    response.delete_cookie('access_token')
    logger.debug("Куки access_token видалено, редирект на /login")
    return response