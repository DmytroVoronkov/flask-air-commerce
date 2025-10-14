from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from config import Config
from database import db
from sqlalchemy import text
import os
import logging
from routes.auth import auth_bp
from routes.users import users_bp
from routes.flights import flights_bp
from routes.tills import tills_bp
from routes.tickets import tickets_bp

# Создание папки logs
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
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
app.config['JWT_SECRET_KEY'] = 'your-secret-key-please-change-this'  # Замените на безопасный ключ
jwt = JWTManager(app)
db.init_app(app)

# Регистрация blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(users_bp)
app.register_blueprint(flights_bp)
app.register_blueprint(tills_bp)
app.register_blueprint(tickets_bp)

# Базовые маршруты
@app.route('/')
def index():
    return jsonify({'message': 'Welcome to the Airline API'})

@app.route('/test-db')
def test_db():
    try:
        db.session.execute(text('SELECT 1'))
        return jsonify({'message': 'Database connection successful'})
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return jsonify({'error': 'Database connection failed'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)