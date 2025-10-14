# --- Alembic env.py (Supabase + psycopg3) ---

from pathlib import Path
import sys
import os
from logging.config import fileConfig

from dotenv import load_dotenv
from alembic import context
from sqlalchemy import engine_from_config, pool

# Make 'app' importable and load backend/.env
BASE_DIR = Path(__file__).resolve().parents[1]  # .../backend
sys.path.insert(0, str(BASE_DIR))
load_dotenv(BASE_DIR / ".env")

# Import SQLAlchemy Base and models (so Alembic sees metadata)
from app.infrastructure.db.base import Base
from app.domain.entities import agent, driver, call_log, feedback  # noqa: F401

# Alembic Config
config = context.config

# Configure logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Return DB URL for Alembic. KEEP +psycopg so it uses psycopg3."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return url  # <-- do NOT strip +psycopg


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        {"sqlalchemy.url": get_url()},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
