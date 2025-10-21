import os
import time
import logging
from urllib.parse import quote
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DatabaseError, OperationalError
from alembic.config import Config
from alembic import command
from dotenv import load_dotenv
from datetime import datetime, timezone
# Імпорти для створення даних
from app import app
from models import db, User, ExchangeRate
from services.user_service import create_user

# Створення папки logs
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(log_dir, 'init_db.log'))
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

def wait_for_db(master_url, max_attempts=20, delay=5):
    """Чекає, поки SQL Server стане доступним."""
    engine = create_engine(master_url, connect_args={'connect_timeout': 10})
    attempt = 1
    while attempt <= max_attempts:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                logger.info("SQL Server is ready")
                return True
        except (DatabaseError, OperationalError) as e:
            logger.warning(f"Attempt {attempt}/{max_attempts} - SQL Server not ready: {e}")
            if attempt == max_attempts:
                logger.error("Failed to connect to SQL Server after maximum attempts")
                return False
            time.sleep(delay)
            attempt += 1
        finally:
            engine.dispose()
    return False

def create_database():
    """Створює базу даних flask_db з collation Cyrillic_General_CI_AS, якщо вона не існує."""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL not set in environment variables")
        raise ValueError("DATABASE_URL not set in environment variables")

    master_url = database_url.replace('flask_db', 'master')
    logger.info(f"Using master URL: {master_url}")

    if not wait_for_db(master_url):
        raise Exception("Cannot connect to SQL Server")

    # Створюємо двигун з AUTOCOMMIT для уникнення транзакцій
    engine = create_engine(master_url, isolation_level='AUTOCOMMIT')

    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 FROM sys.databases WHERE name = :db_name"), {"db_name": "flask_db"})
            exists = result.scalar() is not None
            if not exists:
                conn.execute(text("CREATE DATABASE flask_db COLLATE Cyrillic_General_CI_AS"))
                logger.info("Database 'flask_db' created successfully with Cyrillic_General_CI_AS collation")
            else:
                logger.info("Database 'flask_db' already exists")
                # Перевіряємо collation бази даних
                result = conn.execute(text("SELECT DATABASEPROPERTYEX('flask_db', 'Collation') AS collation"))
                collation = result.scalar()
                logger.info(f"Current collation for flask_db: {collation}")
                if collation != 'Cyrillic_General_CI_AS':
                    logger.warning("Database collation is not Cyrillic_General_CI_AS. Consider updating collation for proper Cyrillic support.")
    except (DatabaseError, OperationalError) as e:
        logger.error(f"Error creating database: {e}")
        raise
    finally:
        engine.dispose()

def apply_migrations():
    """Застосовує міграції Alembic."""
    try:
        alembic_ini_path = "alembic.ini"
        if not os.path.exists(alembic_ini_path):
            logger.error(f"Alembic config file not found at {alembic_ini_path}")
            raise FileNotFoundError(f"Alembic config file not found at {alembic_ini_path}")

        logger.info("Applying Alembic migrations...")
        alembic_cfg = Config(alembic_ini_path)
        command.upgrade(alembic_cfg, "head")
        logger.info("Alembic migrations applied successfully")
    except Exception as e:
        logger.error(f"Error applying migrations: {e}")
        raise

def create_initial_data():
    """Створює початкові дані: адміністратора та курси валют."""
    with app.app_context():
        # Створення адміністратора
        admin_email = 'admin@example.com'
        admin = User.query.filter_by(email=admin_email).first()
        if not admin:
            logger.info("Creating admin user")
            user, success, error_msg = create_user('Admin', admin_email, 'secret', 'admin')
            if success:
                admin = User.query.filter_by(email=admin_email).first()
                if admin and not admin.password_changed and admin.airport_id is None:
                    logger.info("Admin user created with password_changed=False and airport_id=None")
                else:
                    logger.warning("Admin user created but password_changed or airport_id is incorrect")
            else:
                logger.error(f"Failed to create admin user: {error_msg}")
                raise Exception(f"Failed to create admin user: {error_msg}")
        else:
            logger.info("Admin user already exists")
            if not admin.password_changed:
                logger.info("Existing admin user has password_changed=False, requiring password change on next login")

        # Створення курсів валют
        exchange_rates = [
            {'base_currency': 'USD', 'target_currency': 'UAH', 'rate': 41.50, 'valid_at': datetime.now(timezone.utc)},
            {'base_currency': 'EUR', 'target_currency': 'UAH', 'rate': 45.00, 'valid_at': datetime.now(timezone.utc)},
        ]
        for rate_data in exchange_rates:
            if not ExchangeRate.query.filter_by(
                base_currency=rate_data['base_currency'],
                target_currency=rate_data['target_currency'],
                valid_at=rate_data['valid_at']
            ).first():
                rate = ExchangeRate(**rate_data)
                db.session.add(rate)
                logger.info(f"Created exchange rate: {rate_data['base_currency']} -> {rate_data['target_currency']}")

        db.session.commit()

if __name__ == '__main__':
    os.environ["PYTHONUNBUFFERED"] = "1"
    logger.info("Starting database initialization...")
    try:
        create_database()
        apply_migrations()
        create_initial_data()
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        raise