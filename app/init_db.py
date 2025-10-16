import os
import time
import logging
from urllib.parse import quote
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DatabaseError, OperationalError
from alembic.config import Config
from alembic import command
from dotenv import load_dotenv

log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Настройка логирования
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
    """Ждёт, пока SQL Server станет доступен."""
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
    """Создаёт базу данных flask_db, если она не существует."""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL not set in environment variables")
        raise ValueError("DATABASE_URL not set in environment variables")

    master_url = database_url.replace('flask_db', 'master')
    logger.info(f"Using master URL: {master_url}")

    if not wait_for_db(master_url):
        raise Exception("Cannot connect to SQL Server")

    engine = create_engine(master_url, connect_args={'connect_timeout': 10})
    try:
        with engine.connect() as conn:
            conn.execute(text("SET IMPLICIT_TRANSACTIONS OFF"))
            result = conn.execute(text("SELECT 1 FROM sys.databases WHERE name = 'flask_db'"))
            exists = result.scalar() is not None
            if not exists:
                conn.execute(text("CREATE DATABASE flask_db"))
                logger.info("Database 'flask_db' created successfully")
            else:
                logger.info("Database 'flask_db' already exists")
    except (DatabaseError, OperationalError) as e:
        logger.error(f"Error creating database: {e}")
        raise
    finally:
        engine.dispose()

def apply_migrations():
    """Применяет миграции Alembic."""
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

if __name__ == '__main__':
    os.environ["PYTHONUNBUFFERED"] = "1"
    logger.info("Starting database initialization...")
    try:
        create_database()
        apply_migrations()
        logger.info("Database initialization completed")
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        raise