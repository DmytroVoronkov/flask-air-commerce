from flask import Flask, jsonify, redirect, url_for, flash
from flask_jwt_extended import JWTManager
from config import Config
from database import db
from sqlalchemy import text
import os
import logging

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
app.config['SECRET_KEY'] = 'your-flask-secret-key-please-change-this'  # Секретний ключ для сесій
app.config['JWT_SECRET_KEY'] = 'your-secret-key-please-change-this'
app.config['JWT_TOKEN_LOCATION'] = ['cookies', 'headers']
app.config['JWT_ACCESS_COOKIE_NAME'] = 'access_token'
app.config['JWT_COOKIE_CSRF_PROTECT'] = False
app.config['JWT_COOKIE_SECURE'] = False
app.config['JWT_ACCESS_COOKIE_PATH'] = '/'
app.config['JWT_COOKIE_SAMESITE'] = 'Lax'
jwt = JWTManager(app)

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