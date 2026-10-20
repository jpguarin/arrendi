"""Alembic creates `alembic_version` by itself, so no migration of a table protects it."""

import pytest
from sqlalchemy import Engine, text

from tests.conftest import SUPABASE_ROLES


def test_row_security_is_enabled_but_not_forced(admin_engine: Engine) -> None:
    with admin_engine.connect() as connection:
        row = connection.execute(
            text(
                "select relrowsecurity, relforcerowsecurity from pg_class "
                "where relname = 'alembic_version'"
            )
        ).one()

    # Not forced: the owner runs the migrations and must keep writing the version.
    assert tuple(row) == (True, False)


@pytest.mark.parametrize("role", SUPABASE_ROLES)
def test_supabase_data_api_roles_cannot_touch_the_table(admin_engine: Engine, role: str) -> None:
    with admin_engine.connect() as connection:
        allowed = connection.execute(
            text(
                "select privilege from unnest(array['select', 'insert', 'update', 'delete']) "
                "as privilege where has_table_privilege(:role, 'alembic_version', privilege)"
            ),
            {"role": role},
        ).scalars()

        assert allowed.all() == []
