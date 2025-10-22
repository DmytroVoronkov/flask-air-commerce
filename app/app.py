from flask import Flask, jsonify, redirect, url_for, flash
from flask_jwt_extended import JWTManager
from config import Config
from database import db
from sqlalchemy import text
import os
import logging
from utils import datetimeformat, transaction_type_ua
import schedule
import time
import threading
from import_csv import import_csv_data

# Створення папки logs
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Налаштування логування
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(log_dir, 'app.log'))
    ]
)
logger = logging.getLogger(__name__)

# Ініціалізація програми
app = Flask(__name__)
app.config.from_object(Config)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'your-flask-secret-key-please-change-this')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key-please-change-this')
app.config['JWT_TOKEN_LOCATION'] = ['cookies', 'headers']
app.config['JWT_ACCESS_COOKIE_NAME'] = 'access_token'
app.config['JWT_COOKIE_CSRF_PROTECT'] = False
app.config['JWT_COOKIE_SECURE'] = False
app.config['JWT_ACCESS_COOKIE_PATH'] = '/'
app.config['JWT_COOKIE_SAMESITE'] = 'Lax'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 1800  # Токен дійсний 30 хвилин
jwt = JWTManager(app)

# Обробник прострочених токенів
@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    logger.info("JWT token has expired, redirecting to login")
    flash('Ваша сесія закінчилася. Будь ласка, увійдіть знову.', 'error')
    response = redirect(url_for('web.login'))
    response.delete_cookie('access_token')
    return response

# Обробник відсутності токена
@jwt.unauthorized_loader
def unauthorized_callback(error):
    logger.info("No JWT token provided, redirecting to login")
    flash('Будь ласка, увійдіть для доступу до цієї сторінки.', 'error')
    response = redirect(url_for('web.login'))
    response.delete_cookie('access_token')
    return response

# Реєстрація фільтрів Jinja2 із utils.py
app.jinja_env.filters['datetimeformat'] = datetimeformat
app.jinja_env.filters['transaction_type_ua'] = transaction_type_ua
logger.debug("Jinja2 filters 'datetimeformat' and 'transaction_type_ua' registered from utils.py")

# Логування ініціалізації ключів
logger.debug("Ініціалізація Flask з SECRET_KEY і JWT_SECRET_KEY")
logger.debug("Ініціалізація JWTManager з токенами в cookies (access_token) і headers")
db.init_app(app)

# Імпорти blueprints після ініціалізації
from routes.users import users_bp
from routes.web import web_bp
from routes.shifts import shifts_bp
from routes.flights import flights_bp
from routes.tickets import tickets_bp

# Реєстрація blueprints
app.register_blueprint(users_bp)
app.register_blueprint(web_bp)
app.register_blueprint(shifts_bp)
app.register_blueprint(flights_bp)
app.register_blueprint(tickets_bp)

# Базові маршрути
@app.route('/')
def index():
    logger.debug("Редирект із / на /login")
    return redirect(url_for('web.login'))

@app.route('/test-db')
def test_db():
    try:
        db.session.execute(text('SELECT 1'))
        logger.debug("Тест підключення до бази даних успішний")
        return jsonify({'message': 'Database connection successful'})
    except Exception as e:
        logger.error(f"Помилка підключення до бази даних: {e}")
        return jsonify({'error': 'Database connection failed'}), 500

# Налаштування періодичної задачі для імпорту CSV
def run_schedule():
    """Запускає планувальник у окремому потоці."""
    def import_task():
        import_csv_data(app, db)
    
    schedule.every().minute.do(import_task)
    logger.info("Планувальник імпорту CSV запущено")
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    # Запускаємо планувальник у окремому потоці
    scheduler_thread = threading.Thread(target=run_schedule, daemon=True)
    scheduler_thread.start()
    app.run(host='0.0.0.0', port=8000, debug=True)