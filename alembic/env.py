"""Alembic migration environment for PostgreSQL."""
import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy.engine import create_engine
from sqlalchemy.pool import NullPool

# Load environment variables
load_dotenv()

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Get database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Convert asyncpg URL to psycopg2 format for SQLAlchemy
if DATABASE_URL.startswith('postgresql://'):
    # Replace postgresql:// with postgresql+psycopg2:// for SQLAlchemy
    sqlalchemy_url = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg2://', 1)
else:
    sqlalchemy_url = DATABASE_URL


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=sqlalchemy_url,
        target_metadata=None,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Create SQLAlchemy engine for migrations
    connectable = create_engine(
        sqlalchemy_url,
        poolclass=NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=None
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

