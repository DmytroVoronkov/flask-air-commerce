from flask import Blueprint, render_template, request, redirect, url_for, make_response, flash
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, get_jwt
from services.auth_service import authenticate_user
from services.user_service import change_user_password_by_user, get_user_by_id
import logging
logger = logging.getLogger(__name__)

web_bp = Blueprint('web', __name__, template_folder='../templates')

@web_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        logger.debug("Відображення форми входу")
        return render_template('login.html')
   
    # POST: Обробка форми логіну
    try:
        logger.debug(f"Отримано POST-запит на /login з Content-Type: {request.content_type}")
        data = request.form
        email = data.get('email')
        password = data.get('password')
        if not all([email, password]):
            logger.warning(f"Спроба входу з відсутніми полями: {email}")
            flash('Заповніть усі поля', 'error')
            return render_template('login.html')
        # Аутентифікація через сервіс
        user, success, error_msg, requires_password_change = authenticate_user(email, password)
        if not success:
            logger.warning(f"Невдала спроба входу для email: {email}")
            flash('Невірна електронна пошта або пароль', 'error')
            return render_template('login.html')
        # Створюємо токен і зберігаємо в куки
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={'role': user.role.value, 'name': user.name}
        )
        logger.info(f"Успішний вхід для користувача: {email}")
        logger.debug(f"Створено access_token: {access_token}")
       
        # Створюємо відповідь
        response = make_response()
        response.set_cookie(
            'access_token',
            access_token,
            httponly=True,
            secure=False, # False для локальної розробки
            samesite='Lax',
            path='/',
            max_age=1800 # Токен живе 30 хвилин
        )
        # Перенаправлення залежно від password_changed
        if requires_password_change:
            logger.debug(f"Користувач {email} повинен змінити пароль")
            response.headers['Location'] = url_for('web.change_password')
        else:
            response.headers['Location'] = url_for('web.dashboard')
        return response, 302
    except Exception as e:
        logger.error(f"Помилка під час входу: {e}")
        flash('Помилка входу', 'error')
        return render_template('login.html')

@web_bp.route('/change-password', methods=['GET', 'POST'])
@jwt_required()
def change_password():
    user_id = int(get_jwt_identity())
    user, success, error_msg = get_user_by_id(user_id)
    if not success:
        flash(error_msg, 'error')
        return redirect(url_for('web.login'))
    
    if request.method == 'GET':
        return render_template('change_password.html', user_name=user.name)
    
    # POST: Обробка форми зміни пароля
    try:
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not all([current_password, new_password, confirm_password]):
            flash('Заповніть усі поля', 'error')
            return render_template('change_password.html', user_name=user.name)
        
        if new_password != confirm_password:
            flash('Новий пароль і підтвердження не співпадають', 'error')
            return render_template('change_password.html', user_name=user.name)
        
        success, error_msg = change_user_password_by_user(user_id, current_password, new_password)
        if success:
            flash('Пароль успішно змінено!', 'success')
            return redirect(url_for('web.dashboard'))
        else:
            flash(f'Помилка зміни пароля: {error_msg}', 'error')
            return render_template('change_password.html', user_name=user.name)
            
    except Exception as e:
        logger.error(f"Помилка зміни пароля для користувача {user_id}: {e}")
        flash('Не вдалося змінити пароль', 'error')
        return render_template('change_password.html', user_name=user.name)

@web_bp.route('/dashboard')
@jwt_required()
def dashboard():
    from services.till_service import get_cashier_open_till # Перенесений імпорт
   
    current_user = get_jwt()
    user_id = int(current_user['sub'])
    role = current_user['role']
    user_name = current_user.get('name', '')
   
    # Перевірка, чи потрібно змінити пароль
    user, success, error_msg = get_user_by_id(user_id)
    if not success:
        flash(error_msg, 'error')
        return redirect(url_for('web.login'))
    
    if not user.password_changed:
        flash('Будь ласка, змініть свій пароль перед продовженням', 'warning')
        return redirect(url_for('web.change_password'))
   
    # Для касира отримуємо статус каси
    open_till = None
    till_status_message = None
   
    if role == 'cashier':
        open_till, success, message = get_cashier_open_till(user_id)
        if success and open_till:
            till_status_message = f"Каса відкрита з {open_till.opened_at.strftime('%d.%m.%Y %H:%M')}. Загальна сума: {open_till.total_amount:.2f} грн"
        elif success:
            till_status_message = message # "Наразі немає відкритої каси"
        else:
            till_status_message = message # Помилка, наприклад, "Помилка отримання відкритої каси: ..."
   
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