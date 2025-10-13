import os
import logging
import random
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv
from database import db
from models import Flight

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('logs/seed_flights.log')]
)
logger = logging.getLogger(__name__)

load_dotenv()

# Список городов для отправления и назначения
cities = [
    "Київ", "Лондон", "Париж", "Нью-Йорк", "Токіо", "Дубай", "Берлін",
    "Сідней", "Рим", "Сінгапур", "Пекін", "Стамбул", "Бангкок", "Лос-Анджелес"
]

# Генерация уникального номера рейса
def generate_flight_number():
    prefix = random.choice(["SU", "BA", "LH", "AF", "EK", "TK", "SQ"])
    number = random.randint(100, 9999)
    return f"{prefix}{number}"

def seed_flights(num_flights=10):
    """Генерирует и добавляет случайные рейсы в таблицу flights."""
    logger.info(f"Starting seeding {num_flights} flights...")
    
    # Создаём сессию SQLAlchemy
    with db.session() as session:
        for i in range(num_flights):
            try:
                # Выбираем разные города для отправления и назначения
                departure, destination = random.sample(cities, 2)
                
                # Генерируем дату вылета (в пределах следующих 30 дней)
                days_ahead = random.randint(1, 30)
                departure_time = datetime.now() + timedelta(days=days_ahead, hours=random.randint(0, 23))
                
                # Генерируем цену билета (между 50 и 1000 USD)
                ticket_price = round(random.uniform(50.0, 1000.0), 2)
                
                # Генерируем уникальный номер рейса
                flight_number = generate_flight_number()
                
                # Создаём рейс
                flight = Flight(
                    flight_number=flight_number,
                    departure=departure,
                    destination=destination,
                    departure_time=departure_time,
                    ticket_price=ticket_price
                )
                
                session.add(flight)
                logger.info(f"Added flight {flight_number}: {departure} -> {destination}")
                
            except IntegrityError as e:
                logger.warning(f"Failed to add flight {flight_number}: {e} (possibly duplicate flight number)")
                session.rollback()
                continue
            
        try:
            session.commit()
            logger.info(f"Successfully seeded {num_flights} flights")
        except Exception as e:
            logger.error(f"Error committing flights: {e}")
            session.rollback()
            raise

if __name__ == '__main__':
    os.environ["PYTHONUNBUFFERED"] = "1"
    logger.info("Starting flight seeding script...")
    
    # Инициализация приложения Flask для контекста
    from flask import Flask
    from config import Config
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    
    with app.app_context():
        try:
            seed_flights(num_flights=10)  # Можно изменить количество рейсов
            logger.info("Flight seeding completed")
        except Exception as e:
            logger.error(f"Seeding failed: {e}")
            raise