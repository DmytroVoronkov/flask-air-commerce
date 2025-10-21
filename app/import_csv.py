import os
import csv
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from models import Airport, Flight, FlightFare
from services.flight_service import create_flight, create_flight_fare
import logging

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/import_csv.log')
    ]
)
logger = logging.getLogger(__name__)

# Шлях до папки з CSV
data_dir = os.path.join(os.path.dirname(__file__), 'data')

def import_airports(db):
    """Імпортує нові аеропорти з airports.csv."""
    airports_file = os.path.join(data_dir, 'airports.csv')
    if not os.path.exists(airports_file):
        logger.warning(f"Файл {airports_file} не знайдено, пропускаємо імпорт аеропортів")
        return True, {}

    imported_count = 0
    skipped_count = 0

    with open(airports_file, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                code = row['code']
                # Перевірка унікальності code
                existing_airport = db.session.query(Airport).filter_by(code=code).first()
                if existing_airport:
                    logger.info(f"Аеропорт {code} уже існує")
                    skipped_count += 1
                    continue

                # Створення нового аеропорту
                airport = Airport(
                    code=code,
                    name=row['name'],
                    location=row['location']
                )
                db.session.add(airport)
                db.session.commit()
                imported_count += 1
                logger.info(f"Імпортовано новий аеропорт {code}")
            except Exception as e:
                logger.error(f"Помилка обробки аеропорту {row.get('code', 'unknown')}: {e}")
                skipped_count += 1
                db.session.rollback()

    logger.info(f"Імпорт аеропортів: імпортовано {imported_count}, пропущено {skipped_count}")
    return True, {}

def import_flights(db):
    """Імпортує рейси з flights.csv, використовуючи airport_code."""
    flights_file = os.path.join(data_dir, 'flights.csv')
    if not os.path.exists(flights_file):
        logger.warning(f"Файл {flights_file} не знайдено, пропускаємо імпорт рейсів")
        return True, {}

    flight_id_map = {}  # flight_number -> real_id
    imported_count = 0
    skipped_count = 0

    with open(flights_file, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                flight_number = row['flight_number']
                
                # Перевірка унікальності flight_number
                existing_flight = db.session.query(Flight).filter_by(flight_number=flight_number).first()
                if existing_flight:
                    logger.info(f"Рейс {flight_number} уже існує")
                    flight_id_map[flight_number] = existing_flight.id
                    skipped_count += 1
                    continue

                # Знаходимо аеропорти за code
                origin_airport = db.session.query(Airport).filter_by(code=row['origin_airport_code']).first()
                destination_airport = db.session.query(Airport).filter_by(code=row['destination_airport_code']).first()
                
                if not origin_airport or not destination_airport:
                    logger.error(f"Не знайдено аеропорти для рейсу {flight_number}: {row['origin_airport_code']} -> {row['destination_airport_code']}")
                    skipped_count += 1
                    continue

                # Передаємо рядки дат
                flight_data, success, error_msg = create_flight(
                    flight_number=flight_number,
                    origin_airport_id=origin_airport.id,
                    destination_airport_id=destination_airport.id,
                    departure_time=row['departure_time'],
                    arrival_time=row['arrival_time'],
                    aircraft_model=row['aircraft_model'],
                    seat_capacity=int(row['seat_capacity'])
                )
                
                if success:
                    flight_id_map[flight_number] = flight_data['id']
                    imported_count += 1
                    logger.info(f"Імпортовано рейс {flight_number}")
                else:
                    logger.error(f"Помилка імпорту рейсу {flight_number}: {error_msg}")
                    skipped_count += 1
                    
            except Exception as e:
                logger.error(f"Помилка обробки рейсу {row.get('flight_number', 'unknown')}: {e}")
                skipped_count += 1
                db.session.rollback()

    db.session.commit()
    logger.info(f"Імпорт рейсів: імпортовано {imported_count}, пропущено {skipped_count}")
    return True, flight_id_map

def import_flight_fares(db, flight_id_map):
    """Імпортує тарифи з flight_fares.csv, використовуючи flight_number."""
    fares_file = os.path.join(data_dir, 'flight_fares.csv')
    if not os.path.exists(fares_file):
        logger.warning(f"Файл {fares_file} не знайдено, пропускаємо імпорт тарифів")
        return True, {}

    imported_count = 0
    skipped_count = 0

    with open(fares_file, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                flight_number = row['flight_number']
                flight_id = flight_id_map.get(flight_number)
                
                if not flight_id:
                    # Шукаємо рейс за flight_number у БД
                    flight = db.session.query(Flight).filter_by(flight_number=flight_number).first()
                    if flight:
                        flight_id = flight.id
                    else:
                        logger.error(f"Рейс {flight_number} не знайдено для тарифу {row['name']}")
                        skipped_count += 1
                        continue

                # Перевірка унікальності тарифу
                existing_fare = db.session.query(FlightFare).filter_by(
                    flight_id=flight_id, name=row['name']
                ).first()
                if existing_fare:
                    logger.info(f"Тариф {row['name']} для рейсу {flight_number} уже існує")
                    skipped_count += 1
                    continue

                # Створення тарифу
                fare_data, success, error_msg = create_flight_fare(
                    flight_id=flight_id,
                    name=row['name'],
                    base_price=float(row['base_price']),
                    base_currency=row['base_currency'],
                    seat_limit=int(row['seat_limit'])
                )
                
                if success:
                    imported_count += 1
                    logger.info(f"Імпортовано тариф {row['name']} для рейсу {flight_number}")
                else:
                    logger.error(f"Помилка імпорту тарифу {row['name']} для {flight_number}: {error_msg}")
                    skipped_count += 1
                    
            except Exception as e:
                logger.error(f"Помилка обробки тарифу {row.get('name', 'unknown')}: {e}")
                skipped_count += 1
                db.session.rollback()

    db.session.commit()
    logger.info(f"Імпорт тарифів: імпортовано {imported_count}, пропущено {skipped_count}")
    return True, {}

def import_csv_data(app, db):
    """Основна функція для імпорту розумних CSV-файлів."""
    with app.app_context():
        logger.info("Початок імпорту розумних CSV-файлів")
        
        # Імпорт аеропортів
        success_airports, _ = import_airports(db)
        if not success_airports:
            logger.error("Помилка імпорту аеропортів")
            return False, "Помилка імпорту аеропортів"
        
        # Імпорт рейсів
        success_flights, flight_id_map = import_flights(db)
        if not success_flights:
            logger.error("Помилка імпорту рейсів")
            return False, "Помилка імпорту рейсів"
        
        # Імпорт тарифів
        success_fares, _ = import_flight_fares(db, flight_id_map)
        if not success_fares:
            logger.error("Помилка імпорту тарифів")
            return False, "Помилка імпорту тарифів"
        
        logger.info("Імпорт розумних CSV-файлів завершено успішно")
        return True, "Імпорт завершено успішно"

if __name__ == "__main__":
    from app import app, db
    try:
        success, message = import_csv_data(app, db)
        if success:
            logger.info(message)
        else:
            logger.error(message)
    except Exception as e:
        logger.error(f"Критична помилка імпорту: {e}")