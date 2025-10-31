from __future__ import annotations
import os, sys, asyncio, pathlib, logging, traceback
from logging.config import fileConfig
from urllib.parse import quote_plus

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
from sqlmodel import SQLModel

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data.schemas import models

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

pg_user = os.getenv("POSTGRES_USER")
pg_password = os.getenv("POSTGRES_PASSWORD")
pg_db = os.getenv("POSTGRES_DB")
pg_host = os.getenv("POSTGRES_HOST")
pg_port = os.getenv("POSTGRES_PORT")

if not all([pg_user, pg_password, pg_db, pg_host, pg_port]):
    raise RuntimeError(
        "Provide POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_HOST and POSTGRES_PORT for Alembic migrations."
    )

user_q = quote_plus(pg_user)
password_q = quote_plus(pg_password)
db_q = quote_plus(pg_db)
db_url = f"postgresql+asyncpg://{user_q}:{password_q}@{pg_host}:{pg_port}/{db_q}"
print(f"[alembic] sqlalchemy.url = {db_url}", flush=True)

config.set_main_option("sqlalchemy.url", db_url)
target_metadata = SQLModel.metadata

LOCK_TIMEOUT_MS = os.getenv("DB_LOCK_TIMEOUT_MS", "5000")
STMT_TIMEOUT_MS = os.getenv("DB_STATEMENT_TIMEOUT_MS", "60000")

def _mask_db_url(url: str) -> str:
    try:
        scheme, rest = url.split("://", 1)
        user_pwd, host = rest.split("@", 1)
        user, _pwd = user_pwd.split(":", 1)
        return f"{scheme}://{user}:***@{host}"
    except Exception:
        return url

def include_object(obj, name, type_, reflected, compare_to):
    if type_ == "table" and name == "alembic_version":
        return False
    return True

def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_object=include_object,
        render_as_batch=False,
        version_table="alembic_version",
        version_table_schema="public",
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_offline() -> None:
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table="alembic_version",
        version_table_schema="public",
    )
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Online mode: begin a real transaction, ensure version table exists, then migrate."""
    engine = create_async_engine(db_url, poolclass=pool.NullPool, future=True)
    try:
        async with engine.begin() as conn:
            # helpful debug
            row = await conn.exec_driver_sql(
                "select current_database(), current_user, current_schema(), current_schemas(true)"
            )
            print(f"[alembic] target: {row.fetchone()}", flush=True)

            # safe timeouts
            await conn.exec_driver_sql(f"SET lock_timeout = '{LOCK_TIMEOUT_MS}ms'")
            await conn.exec_driver_sql(f"SET statement_timeout = '{STMT_TIMEOUT_MS}ms'")

            # make sure the version table exists in 'public' before Alembic stamps it
            await conn.exec_driver_sql("""
                CREATE TABLE IF NOT EXISTS public.alembic_version (
                    version_num VARCHAR(32) NOT NULL PRIMARY KEY
                )
            """)

            await conn.run_sync(do_run_migrations)
    finally:
        await engine.dispose()

def run():
    logging.getLogger().info(f"alembic: using DB URL: {_mask_db_url(db_url)}")
    try:
        if context.is_offline_mode():
            run_migrations_offline()
        else:
            asyncio.run(run_migrations_online())
    except Exception:
        logging.getLogger().exception("Migration failed with exception:")
        traceback.print_exc()
        raise

run()
