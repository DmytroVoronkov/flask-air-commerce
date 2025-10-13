from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt
from config import Config
from database import db
from models import User, Role, Flight
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
import bcrypt
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('app.log')]
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

        # Создаём JWT-токен с identity как строкой
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
    claims = get_jwt()
    if claims['role'] not in ['admin', 'cashier']:
        logger.warning(f"Access denied for role: {claims['role']}")
        return jsonify({'error': 'Insufficient permissions'}), 403
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)