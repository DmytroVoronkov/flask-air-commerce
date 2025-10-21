"""Test migration
Revision ID: 3672c4b7381d
Revises:
Create Date: 2025-10-10 07:26:39.503227
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '3672c4b7381d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    # Таблиця аеропортів
    op.create_table('airports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=10), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('location', sa.String(length=200), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    
    # Таблиця користувачів
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('password_hash', sa.String(length=256), nullable=False),
        sa.Column('role', sa.Enum('CASHIER', 'ADMIN', 'ACCOUNTANT', 'SALES_MANAGER', name='role'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('password_changed', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('airport_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['airport_id'], ['airports.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    
    # Таблиця кас
    op.create_table('cash_desks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('airport_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['airport_id'], ['airports.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Таблиця рахунків кас
    op.create_table('cash_desk_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cash_desk_id', sa.Integer(), nullable=False),
        sa.Column('currency_code', sa.String(length=3), nullable=False),
        sa.Column('balance', sa.DECIMAL(precision=12, scale=2), nullable=False, server_default='0.0'),
        sa.Column('last_updated', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['cash_desk_id'], ['cash_desks.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Таблиця змін
    op.create_table('shifts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cash_desk_id', sa.Integer(), nullable=False),
        sa.Column('cashier_id', sa.Integer(), nullable=False),
        sa.Column('opened_at', sa.DateTime(), nullable=False),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.Enum('open', 'closed', name='shift_status'), nullable=False),
        sa.CheckConstraint("status = 'open' OR closed_at IS NOT NULL", name='check_shift_status'),
        sa.ForeignKeyConstraint(['cash_desk_id'], ['cash_desks.id'], ),
        sa.ForeignKeyConstraint(['cashier_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_shift_cashier_status', 'shifts', ['cashier_id', 'status'], unique=False)
    
    # Таблиця рейсів
    op.create_table('flights',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('flight_number', sa.String(length=20), nullable=False),
        sa.Column('origin_airport_id', sa.Integer(), nullable=False),
        sa.Column('destination_airport_id', sa.Integer(), nullable=False),
        sa.Column('departure_time', sa.DateTime(), nullable=False),
        sa.Column('arrival_time', sa.DateTime(), nullable=False),
        sa.Column('aircraft_model', sa.String(length=50), nullable=False),
        sa.Column('seat_capacity', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['origin_airport_id'], ['airports.id'], ),
        sa.ForeignKeyConstraint(['destination_airport_id'], ['airports.id'], ),
        sa.CheckConstraint('origin_airport_id != destination_airport_id', name='check_origin_destination'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('flight_number')
    )
    
    # Таблиця тарифів рейсів
    op.create_table('flight_fares',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('flight_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('base_price', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('base_currency', sa.String(length=3), nullable=False),
        sa.Column('seat_limit', sa.Integer(), nullable=False),
        sa.Column('seats_sold', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['flight_id'], ['flights.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Таблиця квитків
    op.create_table('tickets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('flight_id', sa.Integer(), nullable=False),
        sa.Column('flight_fare_id', sa.Integer(), nullable=False),
        sa.Column('shift_id', sa.Integer(), nullable=False),
        sa.Column('passenger_name', sa.String(length=100), nullable=False),
        sa.Column('seat_number', sa.String(length=10), nullable=False),
        sa.Column('price', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('currency_code', sa.String(length=3), nullable=False),
        sa.Column('price_in_base', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('exchange_rate', sa.DECIMAL(precision=10, scale=4), nullable=False),
        sa.Column('sold_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.Enum('sold', 'refunded', name='ticket_status'), nullable=False),
        sa.ForeignKeyConstraint(['flight_id'], ['flights.id'], ),
        sa.ForeignKeyConstraint(['flight_fare_id'], ['flight_fares.id'], ),
        sa.ForeignKeyConstraint(['shift_id'], ['shifts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Таблиця транзакцій
    op.create_table('transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('shift_id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.Enum('sale', 'refund', 'deposit', 'withdrawal', name='transaction_type'), nullable=False),
        sa.Column('amount', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('currency_code', sa.String(length=3), nullable=False),
        sa.Column('reference_type', sa.String(length=50), nullable=True),
        sa.Column('reference_id', sa.Integer(), nullable=True),
        sa.Column('description', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['shift_id'], ['shifts.id'], ),
        sa.ForeignKeyConstraint(['account_id'], ['cash_desk_accounts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Таблиця курсів обміну
    op.create_table('exchange_rates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('base_currency', sa.String(length=3), nullable=False),
        sa.Column('target_currency', sa.String(length=3), nullable=False),
        sa.Column('rate', sa.DECIMAL(precision=10, scale=4), nullable=False),
        sa.Column('valid_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('transactions')
    op.drop_table('tickets')
    op.drop_table('flight_fares')
    op.drop_table('flights')
    op.drop_index('ix_shift_cashier_status', table_name='shifts')
    op.drop_table('shifts')
    op.drop_table('cash_desk_accounts')
    op.drop_table('cash_desks')
    op.drop_table('users')
    op.drop_table('airports')