from database import db
from sqlalchemy import Enum, func
from enum import Enum as PyEnum
import datetime

# Перечислення для ролей
class Role(PyEnum):
    CASHIER = 'cashier'
    ADMIN = 'admin'
    ACCOUNTANT = 'accountant'

# Перечислення для статусу зміни
class ShiftStatus(PyEnum):
    OPEN = 'open'
    CLOSED = 'closed'

# Перечислення для статусу квитка
class TicketStatus(PyEnum):
    SOLD = 'sold'
    REFUNDED = 'refunded'

# Перечислення для типу транзакції
class TransactionType(PyEnum):
    SALE = 'sale'
    REFUND = 'refund'
    DEPOSIT = 'deposit'
    WITHDRAWAL = 'withdrawal'

# Таблиця аеропортів
class Airport(db.Model):
    __tablename__ = 'airports'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    cash_desks = db.relationship('CashDesk', back_populates='airport')
    users = db.relationship('User', back_populates='airport')
    origin_flights = db.relationship('Flight', back_populates='origin_airport', foreign_keys='Flight.origin_airport_id')
    destination_flights = db.relationship('Flight', back_populates='destination_airport', foreign_keys='Flight.destination_airport_id')

# Таблиця кас
class CashDesk(db.Model):
    __tablename__ = 'cash_desks'
    id = db.Column(db.Integer, primary_key=True)
    airport_id = db.Column(db.Integer, db.ForeignKey('airports.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    airport = db.relationship('Airport', back_populates='cash_desks')
    accounts = db.relationship('CashDeskAccount', back_populates='cash_desk')
    shifts = db.relationship('Shift', back_populates='cash_desk')

# Таблиця рахунків кас
class CashDeskAccount(db.Model):
    __tablename__ = 'cash_desk_accounts'
    id = db.Column(db.Integer, primary_key=True)
    cash_desk_id = db.Column(db.Integer, db.ForeignKey('cash_desks.id'), nullable=False)
    currency_code = db.Column(db.String(3), nullable=False)
    balance = db.Column(db.DECIMAL(12, 2), nullable=False, default=0.0)
    last_updated = db.Column(db.DateTime, nullable=False, default=func.current_timestamp())
    cash_desk = db.relationship('CashDesk', back_populates='accounts')
    transactions = db.relationship('Transaction', back_populates='account')

# Таблиця користувачів
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(Enum(Role, name='role'), nullable=False, default=Role.CASHIER)
    created_at = db.Column(db.DateTime, nullable=False, default=func.current_timestamp())
    password_changed = db.Column(db.Boolean, nullable=False, default=False)
    airport_id = db.Column(db.Integer, db.ForeignKey('airports.id'), nullable=True)
    airport = db.relationship('Airport', back_populates='users')
    shifts = db.relationship('Shift', back_populates='cashier')

# Таблиця змін
class Shift(db.Model):
    __tablename__ = 'shifts'
    id = db.Column(db.Integer, primary_key=True)
    cash_desk_id = db.Column(db.Integer, db.ForeignKey('cash_desks.id'), nullable=False)
    cashier_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    opened_at = db.Column(db.DateTime, nullable=False, default=func.current_timestamp())
    closed_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(Enum(ShiftStatus, name='shift_status'), nullable=False, default=ShiftStatus.OPEN)
    cash_desk = db.relationship('CashDesk', back_populates='shifts')
    cashier = db.relationship('User', back_populates='shifts')
    tickets = db.relationship('Ticket', back_populates='shift')
    transactions = db.relationship('Transaction', back_populates='shift')
    __table_args__ = (
        db.CheckConstraint("status = 'open' OR closed_at IS NOT NULL", name='check_shift_status'),
        db.Index('ix_shift_cashier_status', 'cashier_id', 'status'),
    )

# Таблиця рейсів
class Flight(db.Model):
    __tablename__ = 'flights'
    id = db.Column(db.Integer, primary_key=True)
    flight_number = db.Column(db.String(20), unique=True, nullable=False)
    origin_airport_id = db.Column(db.Integer, db.ForeignKey('airports.id'), nullable=False)
    destination_airport_id = db.Column(db.Integer, db.ForeignKey('airports.id'), nullable=False)
    departure_time = db.Column(db.DateTime, nullable=False)
    arrival_time = db.Column(db.DateTime, nullable=False)
    aircraft_model = db.Column(db.String(50), nullable=False)
    seat_capacity = db.Column(db.Integer, nullable=False)
    origin_airport = db.relationship('Airport', back_populates='origin_flights', foreign_keys=[origin_airport_id])
    destination_airport = db.relationship('Airport', back_populates='destination_flights', foreign_keys=[destination_airport_id])
    fares = db.relationship('FlightFare', back_populates='flight')
    tickets = db.relationship('Ticket', back_populates='flight')
    __table_args__ = (
        db.CheckConstraint('origin_airport_id != destination_airport_id', name='check_origin_destination'),
    )

# Таблиця тарифів рейсів
class FlightFare(db.Model):
    __tablename__ = 'flight_fares'
    id = db.Column(db.Integer, primary_key=True)
    flight_id = db.Column(db.Integer, db.ForeignKey('flights.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    base_price = db.Column(db.DECIMAL(10, 2), nullable=False)
    base_currency = db.Column(db.String(3), nullable=False)
    seat_limit = db.Column(db.Integer, nullable=False)
    seats_sold = db.Column(db.Integer, nullable=False, default=0)
    flight = db.relationship('Flight', back_populates='fares')
    tickets = db.relationship('Ticket', back_populates='flight_fare')

# Таблиця квитків
class Ticket(db.Model):
    __tablename__ = 'tickets'
    id = db.Column(db.Integer, primary_key=True)
    flight_id = db.Column(db.Integer, db.ForeignKey('flights.id'), nullable=False)
    flight_fare_id = db.Column(db.Integer, db.ForeignKey('flight_fares.id'), nullable=False)
    shift_id = db.Column(db.Integer, db.ForeignKey('shifts.id'), nullable=False)
    passenger_name = db.Column(db.String(100), nullable=False)
    seat_number = db.Column(db.String(10), nullable=False)
    price = db.Column(db.DECIMAL(10, 2), nullable=False)
    currency_code = db.Column(db.String(3), nullable=False)
    price_in_base = db.Column(db.DECIMAL(10, 2), nullable=False)
    exchange_rate = db.Column(db.DECIMAL(10, 4), nullable=False)
    sold_at = db.Column(db.DateTime, nullable=False, default=func.current_timestamp())
    status = db.Column(Enum(TicketStatus, name='ticket_status'), nullable=False, default=TicketStatus.SOLD)
    flight = db.relationship('Flight', back_populates='tickets')
    flight_fare = db.relationship('FlightFare', back_populates='tickets')
    shift = db.relationship('Shift', back_populates='tickets')

# Таблиця транзакцій
class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    shift_id = db.Column(db.Integer, db.ForeignKey('shifts.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('cash_desk_accounts.id'), nullable=False)
    type = db.Column(Enum(TransactionType, name='transaction_type'), nullable=False)
    amount = db.Column(db.DECIMAL(10, 2), nullable=False)
    currency_code = db.Column(db.String(3), nullable=False)
    reference_type = db.Column(db.String(50), nullable=True)
    reference_id = db.Column(db.Integer, nullable=True)
    description = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=func.current_timestamp())
    shift = db.relationship('Shift', back_populates='transactions')
    account = db.relationship('CashDeskAccount', back_populates='transactions')

# Таблиця курсів обміну
class ExchangeRate(db.Model):
    __tablename__ = 'exchange_rates'
    id = db.Column(db.Integer, primary_key=True)
    base_currency = db.Column(db.String(3), nullable=False)
    target_currency = db.Column(db.String(3), nullable=False)
    rate = db.Column(db.DECIMAL(10, 4), nullable=False)
    valid_at = db.Column(db.DateTime, nullable=False, default=func.current_timestamp())