"""Alembic environment configuration.
Loads the DATABASE_URL from the .env file (via python‑dotenv) and configures
SQLAlchemy's engine for migration commands.
"""
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# -------------------------------------------------------------------
# Load the DATABASE_URL from .env (project root / backend/.env)
# -------------------------------------------------------------------
from pathlib import Path
from dotenv import load_dotenv

# Assume the .env lives one level up from the migrations folder
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=env_path)

# The URL is now available as an environment variable
# Alembic's .ini file uses a placeholder %(DATABASE_URL)s
# which we replace here.
database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise RuntimeError("DATABASE_URL not set – ensure .env contains the Neon connection string.")

# -------------------------------------------------------------------
# Set up the target metadata for 'autogenerate' support.
# -------------------------------------------------------------------
# Import your model Base to let Alembic know about tables.
from backend.models import Base  # noqa: E402
config.set_main_option('sqlalchemy.url', database_url)

target_metadata = Base.metadata

def run_migrations_offline():
    """Run migrations in 'offline' mode.
    This configures the context with just a URL and not an Engine,
    which is useful for generating SQL scripts.
    """
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
    """Run migrations in 'online' mode.
    Here we create an Engine and associate a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
