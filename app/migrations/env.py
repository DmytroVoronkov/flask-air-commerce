import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv
from database import db
from models import *  # Импортируйте все модели

load_dotenv()

# this is the Alembic Config object
config = context.config

# Экранируем символ % в DATABASE_URL
database_url = os.getenv('DATABASE_URL')
if database_url:
    database_url = database_url.replace('%', '%%')

# Устанавливаем sqlalchemy.url
config.set_main_option('sqlalchemy.url', database_url)

# Interpret the config file for Python logging
fileConfig(config.config_file_name)

# add your model's MetaData object here for 'autogenerate' support
target_metadata = db.Model.metadata

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()