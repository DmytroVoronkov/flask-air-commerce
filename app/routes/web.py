from flask import Blueprint, render_template, request, redirect, url_for, make_response
from flask_jwt_extended import create_access_token, jwt_required, get_jwt
from services.auth_service import authenticate_user
from services.user_service import get_user_by_id
import logging

logger = logging.getLogger(__name__)
web_bp = Blueprint('web', __name__, template_folder='templates')

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
            return render_template('login.html', error='Заповніть усі поля')

        # Аутентификация через сервис
        user, success, error_msg = authenticate_user(email, password)
        if not success:
            logger.warning(f"Невдала спроба входу для email: {email}")
            return render_template('login.html', error='Невірна електронна пошта або пароль')

        # Создаём токен и сохраняем в куки
        access_token = create_access_token(
            identity=str(user.id), 
            additional_claims={'role': user.role.value}
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
            max_age=3600  # Токен живёт 1 час
        )
        logger.debug("Куки access_token установлены для редиректа на /dashboard")
        return response

    except Exception as e:
        logger.error(f"Помилка під час входу: {e}")
        return render_template('login.html', error='Помилка входу')

@web_bp.route('/dashboard')
@jwt_required()
def dashboard():
    try:
        claims = get_jwt()
        user_id = int(claims['sub'])
        role = claims['role']
        logger.debug(f"Доступ до панелі керування для користувача {user_id} з роллю {role}, куки: {request.cookies.get('access_token')}")

        # Получаем пользователя
        user, success, error_msg = get_user_by_id(user_id)
        if not success:
            logger.warning(f"Користувача {user_id} не знайдено для панелі керування")
            return redirect(url_for('web.login'))

        logger.info(f"Користувач {user_id} отримав доступ до панелі керування")
        return render_template('dashboard.html', 
                            user_name=user.name, 
                            user_role=role)

    except Exception as e:
        logger.error(f"Помилка доступу до панелі керування для користувача {user_id}: {e}")
        return redirect(url_for('web.login'))

@web_bp.route('/logout')
def logout():
    logger.debug("Удаление куки access_token при выходе")
    response = make_response(redirect(url_for('web.login')))
    response.delete_cookie('access_token', path='/')
    logger.info("Користувач вийшов із системи")
    return response