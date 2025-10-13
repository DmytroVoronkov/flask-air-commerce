from flask import Flask, request, jsonify
from config import Config
from database import db
from models import User, Role
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
import bcrypt
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

@app.route('/')
def index():
    return '<h1>Hello, Flask with SQLAlchemy and SQL Server!</h1>'

@app.route('/test-db')
def test_db():
    try:
        db.session.execute(text('SELECT 1'))
        return '✅ Database connection successful!'
    except Exception as e:
        return f'❌ Database connection failed: {e}'

@app.route('/users', methods=['GET', 'POST'])
def users():
    if request.method == 'GET':
        try:
            # Получаем всех пользователей
            users = User.query.all()
            users_list = [
                {
                    'id': user.id,
                    'name': user.name,
                    'email': user.email,
                    'role': user.role.value,
                    'created_at': user.created_at.isoformat()
                } for user in users
            ]
            logger.info("Retrieved user list")
            return jsonify(users_list)
        except Exception as e:
            logger.error(f"Error retrieving users: {e}")
            return jsonify({'error': 'Failed to retrieve users'}), 500

    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No input data provided'}), 400

            # Валидация входных данных
            name = data.get('name')
            email = data.get('email')
            password = data.get('password')
            role = data.get('role')

            if not all([name, email, password, role]):
                return jsonify({'error': 'Missing required fields'}), 400

            if role not in [r.value for r in Role]:
                return jsonify({'error': f"Invalid role. Must be one of: {[r.value for r in Role]}"}), 400

            # Хэшируем пароль
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            # Создаём пользователя
            user = User(
                name=name,
                email=email,
                password_hash=password_hash,
                role=Role[role.upper()]
            )

            db.session.add(user)
            db.session.commit()
            logger.info(f"Created user: {email}")
            return jsonify({
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'role': user.role.value,
                'created_at': user.created_at.isoformat()
            }), 201

        except IntegrityError:
            db.session.rollback()
            logger.error(f"Error creating user: Email {email} already exists")
            return jsonify({'error': 'Email already exists'}), 400
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating user: {e}")
            return jsonify({'error': 'Failed to create user'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)