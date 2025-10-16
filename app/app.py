from flask import Flask, jsonify, redirect, url_for, flash
from flask_jwt_extended import JWTManager
from config import Config
from database import db
from sqlalchemy import text
import os
import logging
from utils import datetimeformat

# Создание папки logs
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(log_dir, 'app.log'))
    ]
)
logger = logging.getLogger(__name__)

# Инициализация приложения
app = Flask(__name__)
app.config.from_object(Config)
app.config['SECRET_KEY'] = 'your-flask-secret-key-please-change-this'
app.config['JWT_SECRET_KEY'] = 'your-secret-key-please-change-this'
app.config['JWT_TOKEN_LOCATION'] = ['cookies', 'headers']
app.config['JWT_ACCESS_COOKIE_NAME'] = 'access_token'
app.config['JWT_COOKIE_CSRF_PROTECT'] = False
app.config['JWT_COOKIE_SECURE'] = False
app.config['JWT_ACCESS_COOKIE_PATH'] = '/'
app.config['JWT_COOKIE_SAMESITE'] = 'Lax'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 1800  # Токен дійсний 30 хвилин (1800 секунд)
jwt = JWTManager(app)

# Обробник прострочених токенів
@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    logger.info("JWT token has expired, redirecting to login")
    flash('Ваша сесія закінчилася. Будь ласка, увійдіть знову.', 'error')
    response = redirect(url_for('web.login'))
    response.delete_cookie('access_token')  # Видаляємо прострочений токен
    return response

# Обробник відсутності токена
@jwt.unauthorized_loader
def unauthorized_callback(error):
    logger.info("No JWT token provided, redirecting to login")
    flash('Будь ласка, увійдіть для доступу до цієї сторінки.', 'error')
    response = redirect(url_for('web.login'))
    response.delete_cookie('access_token')  # Видаляємо токен, якщо він є
    return response

# Реєстрація фільтра Jinja2 із utils.py
app.jinja_env.filters['datetimeformat'] = datetimeformat
logger.debug("Jinja2 filter 'datetimeformat' registered from utils.py")

# Логирование инициализации ключей
logger.debug("Инициализация Flask с SECRET_KEY и JWT_SECRET_KEY")
logger.debug("Инициализация JWTManager с токенами в cookies (access_token) и headers")

db.init_app(app)

# Імпорти blueprints після ініціалізації
from routes.users import users_bp
from routes.flights import flights_bp
from routes.tills import tills_bp
from routes.tickets import tickets_bp
from routes.web import web_bp

# Регистрация blueprints
app.register_blueprint(users_bp)
app.register_blueprint(flights_bp)
app.register_blueprint(tills_bp)
app.register_blueprint(tickets_bp)
app.register_blueprint(web_bp)

# Базовые маршруты
@app.route('/')
def index():
    logger.debug("Редирект с / на /login")
    return redirect(url_for('web.login'))

@app.route('/test-db')
def test_db():
    try:
        db.session.execute(text('SELECT 1'))
        logger.debug("Тест подключения к базе данных успешен")
        return jsonify({'message': 'Database connection successful'})
    except Exception as e:
        logger.error(f"Ошибка подключения к базе данных: {e}")
        return jsonify({'error': 'Database connection failed'}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Створюємо таблиці, якщо вони ще не створені
    app.run(host='0.0.0.0', port=8000, debug=True)