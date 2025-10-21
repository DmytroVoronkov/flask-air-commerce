import os
import csv
from datetime import datetime, timedelta
from faker import Faker
import random
import logging
from app import app, db
from models import Airport, Flight

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/generate_csv.log')
    ]
)
logger = logging.getLogger(__name__)

# Ініціалізація Faker
fake = Faker('uk_UA')

# Створення папки data/
data_dir = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(data_dir, exist_ok=True)

# Список можливих моделей літаків
aircraft_models = [
    'Boeing 737', 'Boeing 777', 'Airbus A320', 'Airbus A330',
    'Embraer E175', 'Bombardier CRJ900'
]

# Список можливих валют
currencies = ['USD', 'EUR']

# Список можливих назв тарифів
fare_names = ['Economy', 'Business', 'Premium Economy']

# Фіксований список реальних українських аеропортів з IATA кодами
real_airports = [
    {'code': 'KBP', 'name': 'Міжнародний аеропорт "Бориспіль"', 'location': 'Київ, Україна'},
    {'code': 'LWO', 'name': 'Міжнародний аеропорт "Львів"', 'location': 'Львів, Україна'},
    {'code': 'ODS', 'name': 'Міжнародний аеропорт "Одеса"', 'location': 'Одеса, Україна'},
    {'code': 'DOK', 'name': 'Міжнародний аеропорт "Дніпро"', 'location': 'Дніпро, Україна'},
    {'code': 'HRK', 'name': 'Міжнародний аеропорт "Харків"', 'location': 'Харків, Україна'},
    {'code': 'IEV', 'name': 'Міжнародний аеропорт "Київ"', 'location': 'Київ, Україна'},
    {'code': 'GME', 'name': 'Міжнародний аеропорт "Запоріжжя"', 'location': 'Запоріжжя, Україна'},
    {'code': 'KRQ', 'name': 'Міжнародний аеропорт "Кривий Ріг"', 'location': 'Кривий Ріг, Україна'},
    {'code': 'RWN', 'name': 'Міжнародний аеропорт "Рівне"', 'location': 'Рівне, Україна'},
    {'code': 'CWC', 'name': 'Міжнародний аеропорт "Чернівці"', 'location': 'Чернівці, Україна'},
    {'code': 'KHE', 'name': 'Міжнародний аеропорт "Херсон"', 'location': 'Херсон, Україна'},
    {'code': 'KHC', 'name': 'Міжнародний аеропорт "Чернігів"', 'location': 'Чернігів, Україна'},
    {'code': 'VIN', 'name': 'Міжнародний аеропорт "Вінниця"', 'location': 'Вінниця, Україна'},
    {'code': 'UDJ', 'name': 'Міжнародний аеропорт "Ужгород"', 'location': 'Ужгород, Україна'},
    {'code': 'MPJ', 'name': 'Міжнародний аеропорт "Миколаїв"', 'location': 'Миколаїв, Україна'},
    {'code': 'SEV', 'name': 'Міжнародний аеропорт "Сєвєродонецьк"', 'location': 'Сєвєродонецьк, Україна'},
    {'code': 'ZTR', 'name': 'Міжнародний аеропорт "Житомир"', 'location': 'Житомир, Україна'},
    {'code': 'IFO', 'name': 'Міжнародний аеропорт "Івано-Франківськ"', 'location': 'Івано-Франківськ, Україна'},
    {'code': 'PBH', 'name': 'Міжнародний аеропорт "Полтава"', 'location': 'Полтава, Україна'},
    {'code': 'HMD', 'name': 'Міжнародний аеропорт "Хмільник"', 'location': 'Хмільник, Україна'}
]

def get_existing_airports():
    """Отримує існуючі аеропорти з бази даних."""
    try:
        with app.app_context():
            airports = db.session.query(Airport).all()
            return [
                {
                    'code': airport.code,
                    'name': airport.name,
                    'location': airport.location,
                    'id': airport.id
                } for airport in airports
            ]
    except Exception as e:
        logger.error(f"Помилка отримання аеропортів: {e}")
        return []

def get_existing_flights():
    """Отримує існуючі рейси з бази даних."""
    try:
        with app.app_context():
            flights = db.session.query(Flight).all()
            return {
                flight.flight_number: {
                    'id': flight.id,
                    'origin_airport_code': flight.origin_airport.code,
                    'destination_airport_code': flight.destination_airport.code
                } for flight in flights
            }
    except Exception as e:
        logger.error(f"Помилка отримання рейсів: {e}")
        return {}

def generate_airports_csv(num_new_airports=3):
    """Генерує або оновлює airports.csv з реальними аеропортами України."""
    airports_file = os.path.join(data_dir, 'airports.csv')
    fieldnames = ['code', 'name', 'location']

    existing_airports = get_existing_airports()
    logger.info(f"Знайдено {len(existing_airports)} існуючих аеропортів")

    # Фільтруємо реальні аеропорти, які ще не існують у БД
    existing_codes = {airport['code'] for airport in existing_airports}
    available_real_airports = [ap for ap in real_airports if ap['code'] not in existing_codes]

    new_airports = []

    with open(airports_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        # Записуємо існуючі аеропорти
        for airport in existing_airports:
            writer.writerow({
                'code': airport['code'],
                'name': airport['name'],
                'location': airport['location']
            })

        # Генеруємо нові аеропорти з реального списку (вибираємо випадково, щоб не перевищити num_new_airports)
        selected_new = random.sample(available_real_airports, min(num_new_airports, len(available_real_airports)))
        for airport_data in selected_new:
            writer.writerow({
                'code': airport_data['code'],
                'name': airport_data['name'],
                'location': airport_data['location']
            })
            new_airports.append({
                'code': airport_data['code'],
                'name': airport_data['name'],
                'location': airport_data['location']
            })

    logger.info(f"Оновлено airports.csv: {len(existing_airports)} існуючих + {len(new_airports)} нових з реального списку")
    return existing_airports + new_airports

def generate_flights_csv(airports, num_new_flights=5):
    """Генерує або оновлює flights.csv на основі стану БД."""
    flights_file = os.path.join(data_dir, 'flights.csv')
    fieldnames = [
        'flight_number', 'origin_airport_code', 'destination_airport_code',
        'departure_time', 'arrival_time', 'aircraft_model', 'seat_capacity'
    ]

    existing_flights = get_existing_flights()
    logger.info(f"Знайдено {len(existing_flights)} існуючих рейсів")

    new_flights = []
    used_flight_numbers = set(existing_flights.keys())

    with open(flights_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        # Записуємо існуючі рейси
        for flight_number, flight_data in existing_flights.items():
            writer.writerow({
                'flight_number': flight_number,
                'origin_airport_code': flight_data['origin_airport_code'],
                'destination_airport_code': flight_data['destination_airport_code'],
                'departure_time': '',
                'arrival_time': '',
                'aircraft_model': '',
                'seat_capacity': 0
            })

        # Генеруємо нові рейси
        for i in range(num_new_flights):
            while True:
                flight_number = f"FL{random.randint(100, 999)}"
                if flight_number not in used_flight_numbers:
                    break
            used_flight_numbers.add(flight_number)

            origin_airport = random.choice(airports)
            destination_airport = random.choice([a for a in airports if a['code'] != origin_airport['code']])
            departure_time = fake.date_time_between(start_date='now', end_date='+30d')
            arrival_time = departure_time + timedelta(hours=random.randint(1, 4))
            aircraft_model = random.choice(aircraft_models)
            seat_capacity = random.randint(100, 300)

            writer.writerow({
                'flight_number': flight_number,
                'origin_airport_code': origin_airport['code'],
                'destination_airport_code': destination_airport['code'],
                'departure_time': departure_time.strftime('%Y-%m-%dT%H:%M'),
                'arrival_time': arrival_time.strftime('%Y-%m-%dT%H:%M'),
                'aircraft_model': aircraft_model,
                'seat_capacity': seat_capacity
            })

            new_flights.append({
                'flight_number': flight_number,
                'origin_airport_code': origin_airport['code'],
                'destination_airport_code': destination_airport['code'],
                'departure_time': departure_time,
                'arrival_time': arrival_time,
                'aircraft_model': aircraft_model,
                'seat_capacity': seat_capacity
            })

    logger.info(f"Оновлено flights.csv: додано {len(new_flights)} нових рейсів")
    return new_flights

def generate_flight_fares_csv(new_flights):
    """Генерує flight_fares.csv для нових рейсів, з сумою seat_limit = seat_capacity."""
    fares_file = os.path.join(data_dir, 'flight_fares.csv')
    fieldnames = ['flight_number', 'name', 'base_price', 'base_currency', 'seat_limit', 'seats_sold']

    with open(fares_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for flight in new_flights:
            seat_capacity = flight['seat_capacity']
            num_fares = random.randint(1, 3)
            
            # Генеруємо seat_limit для кожного тарифу так, щоб сума дорівнювала seat_capacity
            seat_limits = []
            for _ in range(num_fares - 1):
                limit = random.randint(10, seat_capacity // num_fares)
                seat_limits.append(limit)
            # Останній тариф отримує решту місць
            last_limit = seat_capacity - sum(seat_limits)
            if last_limit < 10:
                # Якщо останній менше 10, перерозподіляємо
                seat_limits[-1] += last_limit - 10 if len(seat_limits) > 0 else 0
                last_limit = 10
            seat_limits.append(last_limit)
            
            # Генеруємо назви тарифів (унікальні для рейсу)
            generated_fare_names = random.sample(fare_names * 2, num_fares)  # Дублюємо список для можливості більше 3 тарифів
            
            for i in range(num_fares):
                name = generated_fare_names[i]
                base_price = round(random.uniform(50, 500), 2)
                base_currency = random.choice(currencies)
                seat_limit = seat_limits[i]
                seats_sold = 0

                writer.writerow({
                    'flight_number': flight['flight_number'],
                    'name': name,
                    'base_price': base_price,
                    'base_currency': base_currency,
                    'seat_limit': seat_limit,
                    'seats_sold': seats_sold
                })

    logger.info(f"Згенеровано тарифи для {len(new_flights)} рейсів у {fares_file} (сума seat_limit = seat_capacity)")

def generate_smart_csv(num_new_airports=3, num_new_flights=5):
    """Генерує розумні CSV-файли залежно від стану БД."""
    logger.info("Початок генерації розумних CSV-файлів")

    # Генеруємо/оновлюємо аеропорти з реальних даних
    all_airports = generate_airports_csv(num_new_airports)

    # Генеруємо рейси
    new_flights = generate_flights_csv(all_airports, num_new_flights)

    # Генеруємо тарифи з перевіркою суми seat_limit
    generate_flight_fares_csv(new_flights)

    logger.info("Генерація розумних CSV-файлів завершена")

if __name__ == "__main__":
    try:
        generate_smart_csv(num_new_airports=2, num_new_flights=3)
    except Exception as e:
        logger.error(f"Помилка генерації CSV: {e}")
        raise