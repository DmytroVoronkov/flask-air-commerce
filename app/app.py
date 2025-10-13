from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt
from config import Config
from database import db
from datetime import datetime 
from models import User, Role, Flight, Till
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
import bcrypt
import logging
import os

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

app = Flask(__name__)
app.config.from_object(Config)
app.config['JWT_SECRET_KEY'] = 'your-secret-key-please-change-this'  # Замените на безопасный ключ в продакшене
jwt = JWTManager(app)
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

            name = data.get('name')
            email = data.get('email')
            password = data.get('password')
            role = data.get('role')

            if not all([name, email, password, role]):
                return jsonify({'error': 'Missing required fields'}), 400

            if role not in [r.value for r in Role]:
                return jsonify({'error': f"Invalid role. Must be one of: {[r.value for r in Role]}"}), 400

            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

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

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No input data provided'}), 400

        email = data.get('email')
        password = data.get('password')

        if not all([email, password]):
            return jsonify({'error': 'Missing email or password'}), 400

        user = User.query.filter_by(email=email).first()
        if not user or not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            logger.warning(f"Failed login attempt for email: {email}")
            return jsonify({'error': 'Invalid email or password'}), 401

        access_token = create_access_token(identity=str(user.id), additional_claims={'role': user.role.value})
        logger.info(f"Successful login for user: {email}")
        return jsonify({
            'access_token': access_token,
            'role': user.role.value,
            'name': user.name
        }), 200

    except Exception as e:
        logger.error(f"Error during login: {e}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/flights', methods=['GET'])
@jwt_required()
def flights():
    try:
        flights = Flight.query.all()
        flights_list = [
            {
                'id': flight.id,
                'flight_number': flight.flight_number,
                'departure': flight.departure,
                'destination': flight.destination,
                'departure_time': flight.departure_time.isoformat(),
                'ticket_price': str(flight.ticket_price),
                'created_at': flight.created_at.isoformat()
            } for flight in flights
        ]
        logger.info("Retrieved flights list")
        return jsonify(flights_list)
    except Exception as e:
        logger.error(f"Error retrieving flights: {e}")
        return jsonify({'error': 'Failed to retrieve flights'}), 500

@app.route('/tills', methods=['GET'])
@jwt_required()
def tills():
    try:
        claims = get_jwt()
        user_id = int(claims['sub'])
        role = claims['role']
        logger.info(f"User {user_id} with role {role} requested tills")

        # Фильтрация для кассиров: только их кассы
        if role == 'cashier':
            tills = Till.query.filter_by(cashier_id=user_id).all()
        else:
            # Администраторы и бухгалтеры видят все кассы
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
        return jsonify(tills_list)
    except Exception as e:
        logger.error(f"Error retrieving tills: {e}")
        return jsonify({'error': 'Failed to retrieve tills'}), 500

# Проверка статуса открытых касс
@app.route('/tills/open', methods=['GET'])
@jwt_required()
def check_open_till():
    try:
        claims = get_jwt()
        user_id = int(claims['sub'])
        role = claims['role']
        logger.info(f"User {user_id} with role {role} checking open tills")

        open_till = Till.query.filter_by(is_active=True).first()
        if open_till:
            return jsonify({
                'is_open': True,
                'till_id': open_till.id,
                'cashier_id': open_till.cashier_id,
                'cashier_name': open_till.cashier.name,
                'cashier_email': open_till.cashier.email,
                'opened_at': open_till.opened_at.isoformat(),
                'total_amount': str(open_till.total_amount)
            }), 200
        return jsonify({'is_open': False}), 200
    except Exception as e:
        logger.error(f"Error checking open till: {e}")
        return jsonify({'error': 'Failed to check open till'}), 500

# Открытие кассы
@app.route('/tills/open', methods=['POST'])
@jwt_required()
def open_till():
    try:
        claims = get_jwt()
        user_id = int(claims['sub'])
        role = claims['role']
        logger.info(f"User {user_id} with role {role} attempting to open a till")

        # Проверка роли
        if role != Role.CASHIER.value:
            logger.warning(f"User {user_id} with role {role} attempted to open a till")
            return jsonify({'error': 'Only cashiers can open tills'}), 403

        # Проверка, нет ли открытых касс
        if Till.query.filter_by(is_active=True).count() > 0:
            logger.warning(f"User {user_id} attempted to open a till while another is active")
            return jsonify({'error': 'Another till is already open'}), 400

        # Создаём новую кассу
        new_till = Till(
            cashier_id=user_id,
            opened_at=datetime.now(),
            is_active=True,
            total_amount=0.0
        )
        db.session.add(new_till)
        db.session.commit()
        logger.info(f"User {user_id} opened till {new_till.id}")

        return jsonify({
            'message': 'Till opened successfully',
            'till_id': new_till.id,
            'cashier_id': new_till.cashier_id,
            'opened_at': new_till.opened_at.isoformat(),
            'total_amount': str(new_till.total_amount)
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error opening till for user {user_id}: {e}")
        return jsonify({'error': 'Failed to open till'}), 500

# Закрытие кассы
@app.route('/tills/close', methods=['POST'])
@jwt_required()
def close_till():
    try:
        claims = get_jwt()
        user_id = int(claims['sub'])
        role = claims['role']
        logger.info(f"User {user_id} with role {role} attempting to close a till")

        # Проверка роли
        if role != Role.CASHIER.value:
            logger.warning(f"User {user_id} with role {role} attempted to close a till")
            return jsonify({'error': 'Only cashiers can close tills'}), 403

        # Находим открытую кассу текущего кассира
        open_till = Till.query.filter_by(cashier_id=user_id, is_active=True).first()
        if not open_till:
            logger.warning(f"No open till found for user {user_id}")
            return jsonify({'error': 'No open till found for this cashier'}), 404

        # Закрываем кассу
        open_till.is_active = False
        open_till.closed_at = datetime.now()
        db.session.commit()
        logger.info(f"User {user_id} closed till {open_till.id}")

        return jsonify({
            'message': 'Till closed successfully',
            'till_id': open_till.id,
            'closed_at': open_till.closed_at.isoformat()
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error closing till for user {user_id}: {e}")
        return jsonify({'error': 'Failed to close till'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)