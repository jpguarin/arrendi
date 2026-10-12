"""Leaves the end-to-end database empty and migrated. Run with the API's Python.

A database of its own (`arrendi_e2e`), apart from the one pytest uses, and always local:
the end-to-end run never touches Supabase.
"""

import os
import sys

from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.db import create_db_engine, to_psycopg_url
from tests.conftest import APP_ROLES, LOCAL_HOSTS, ROLE_PASSWORD, alembic_config

url = make_url(os.environ.get("E2E_DATABASE_URL", "postgresql://localhost:5432/arrendi_e2e"))
if url.host not in LOCAL_HOSTS:
    sys.exit("E2E_DATABASE_URL must point to a local PostgreSQL, never to Supabase")
admin_url = url.render_as_string(hide_password=False)

# The database itself, the first time. `create database` cannot run in a transaction.
server = create_engine(
    to_psycopg_url(url.set(database="postgres").render_as_string(hide_password=False)),
    isolation_level="AUTOCOMMIT",
)
with server.connect() as connection:
    exists = connection.execute(
        text("select 1 from pg_database where datname = :name"), {"name": url.database}
    ).first()
    if not exists:
        connection.execute(text(f'create database "{url.database}"'))
server.dispose()

engine = create_db_engine(admin_url)
with engine.begin() as connection:
    connection.execute(text("drop schema public cascade"))
    connection.execute(text("create schema public"))
command.upgrade(alembic_config(admin_url), "head")
# The migration creates the app roles without login; each environment enables it by hand.
with engine.begin() as connection:
    for role in APP_ROLES:
        connection.execute(text(f"alter role {role} with login password '{ROLE_PASSWORD}'"))
engine.dispose()
print(f"{url.database} is empty and migrated")
