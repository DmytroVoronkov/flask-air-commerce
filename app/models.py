from database import db
from sqlalchemy import Enum, func
from enum import Enum as PyEnum
import datetime

# Определение ролей как перечисления
class Role(PyEnum):
    CASHIER = 'cashier'
    ADMIN = 'admin'
    ACCOUNTANT = 'accountant'

# Таблица пользователей
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)  # Хэш пароля
    role = db.Column(Enum(Role, name='role'), nullable=False, default=Role.CASHIER)
    created_at = db.Column(db.DateTime, nullable=False, default=func.current_timestamp())

    # Связь с кассами
    tills = db.relationship('Till', back_populates='cashier')

# Таблица касс (смен кассира)
class Till(db.Model):
    __tablename__ = 'tills'
    id = db.Column(db.Integer, primary_key=True)
    cashier_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    opened_at = db.Column(db.DateTime, nullable=False, default=func.current_timestamp())
    closed_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)  # Статус: открыта/закрыта
    total_amount = db.Column(db.DECIMAL(10, 2), nullable=False, default=0.0)  # Сумма продаж

    # Связь с пользователем и билетами
    cashier = db.relationship('User', back_populates='tills')
    tickets = db.relationship('Ticket', back_populates='till')

    # Ограничение: только одна открытая касса на кассира
    __table_args__ = (
        db.CheckConstraint('is_active = 1 OR closed_at IS NOT NULL', name='check_till_status'),
        db.Index('ix_till_cashier_active', 'cashier_id', 'is_active'),
    )

# Таблица рейсов
class Flight(db.Model):
    __tablename__ = 'flights'
    id = db.Column(db.Integer, primary_key=True)
    flight_number = db.Column(db.String(20), unique=True, nullable=False)
    departure = db.Column(db.String(100), nullable=False)  # Пункт отправления
    destination = db.Column(db.String(100), nullable=False)  # Пункт назначения
    departure_time = db.Column(db.DateTime, nullable=False)
    ticket_price = db.Column(db.DECIMAL(10, 2), nullable=False)  # Цена билета
    created_at = db.Column(db.DateTime, nullable=False, default=func.current_timestamp())

    # Связь с билетами
    tickets = db.relationship('Ticket', back_populates='flight')

# Таблица билетов
class Ticket(db.Model):
    __tablename__ = 'tickets'
    id = db.Column(db.Integer, primary_key=True)
    till_id = db.Column(db.Integer, db.ForeignKey('tills.id'), nullable=False)
    flight_id = db.Column(db.Integer, db.ForeignKey('flights.id'), nullable=False)
    passenger_name = db.Column(db.String(100), nullable=False)
    passenger_passport = db.Column(db.String(50), nullable=False)
    price = db.Column(db.DECIMAL(10, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='sold')  # sold/returned
    sold_at = db.Column(db.DateTime, nullable=False, default=func.current_timestamp())

    # Связь с кассой и рейсом
    till = db.relationship('Till', back_populates='tickets')
    flight = db.relationship('Flight', back_populates='tickets')