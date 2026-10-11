"""An owner can never read or change another owner's data."""

from uuid import UUID, uuid4

import pytest
from alembic import command
from sqlalchemy import Engine, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.db import set_owner_id
from app.models import Owner
from tests.conftest import alembic_config

ALL_NAMES = text("select name from owners order by name")


def test_owner_sees_only_their_own_row(api_engine: Engine, two_owners: tuple[UUID, UUID]) -> None:
    ana, beto = two_owners

    with api_engine.begin() as connection:
        set_owner_id(connection, ana)
        assert connection.execute(ALL_NAMES).scalars().all() == ["Ana"]

    with api_engine.begin() as connection:
        set_owner_id(connection, beto)
        assert connection.execute(ALL_NAMES).scalars().all() == ["Beto"]


def test_owner_sees_only_their_own_row_through_the_model(
    api_engine: Engine, two_owners: tuple[UUID, UUID]
) -> None:
    ana, beto = two_owners

    with Session(api_engine) as session, session.begin():
        set_owner_id(session, ana)
        assert [owner.id for owner in session.scalars(select(Owner))] == [ana]
        assert session.get(Owner, beto) is None


def test_owner_cannot_update_another_owner(
    api_engine: Engine, admin_engine: Engine, two_owners: tuple[UUID, UUID]
) -> None:
    ana, beto = two_owners

    with api_engine.begin() as connection:
        set_owner_id(connection, ana)
        result = connection.execute(
            text("update owners set name = 'Hackeado' where id = :id"), {"id": beto}
        )
        assert result.rowcount == 0

    with admin_engine.connect() as connection:
        name = connection.execute(text("select name from owners where id = :id"), {"id": beto})
        assert name.scalar_one() == "Beto"


def test_owner_cannot_insert_a_row_for_someone_else(
    api_engine: Engine, two_owners: tuple[UUID, UUID]
) -> None:
    ana, _ = two_owners

    with pytest.raises(DBAPIError, match="row-level security"), api_engine.begin() as connection:
        set_owner_id(connection, ana)
        connection.execute(
            text("insert into owners (id, name, email) values (:id, 'Otro', 'otro@example.com')"),
            {"id": uuid4()},
        )


def test_owner_cannot_move_their_row_to_another_id(
    api_engine: Engine, two_owners: tuple[UUID, UUID]
) -> None:
    ana, _ = two_owners

    with pytest.raises(DBAPIError, match="row-level security"), api_engine.begin() as connection:
        set_owner_id(connection, ana)
        connection.execute(
            text("update owners set id = :new where id = :id"), {"new": uuid4(), "id": ana}
        )


def test_owner_cannot_delete_rows(api_engine: Engine, two_owners: tuple[UUID, UUID]) -> None:
    ana, beto = two_owners

    with pytest.raises(DBAPIError, match="permission denied"), api_engine.begin() as connection:
        set_owner_id(connection, ana)
        connection.execute(text("delete from owners where id = :id"), {"id": beto})


def test_without_an_owner_no_row_is_visible(
    api_engine: Engine, two_owners: tuple[UUID, UUID]
) -> None:
    with api_engine.begin() as connection:
        assert connection.execute(ALL_NAMES).scalars().all() == []


def test_owner_does_not_leak_to_the_next_transaction(
    api_engine: Engine, two_owners: tuple[UUID, UUID]
) -> None:
    """The pooler hands the same connection to different requests."""
    ana, _ = two_owners

    with api_engine.connect() as connection:
        with connection.begin():
            set_owner_id(connection, ana)
            assert connection.execute(ALL_NAMES).scalars().all() == ["Ana"]
        with connection.begin():
            assert connection.execute(ALL_NAMES).scalars().all() == []


def test_tasks_role_sees_every_owner(tasks_engine: Engine, two_owners: tuple[UUID, UUID]) -> None:
    with tasks_engine.begin() as connection:
        assert connection.execute(ALL_NAMES).scalars().all() == ["Ana", "Beto"]


def test_row_security_is_enabled_and_forced(admin_engine: Engine) -> None:
    with admin_engine.connect() as connection:
        row = connection.execute(
            text(
                "select relrowsecurity, relforcerowsecurity from pg_class where relname = 'owners'"
            )
        ).one()

    assert tuple(row) == (True, True)


def test_api_role_cannot_bypass_the_policies(admin_engine: Engine) -> None:
    with admin_engine.connect() as connection:
        roles = connection.execute(
            text(
                "select rolname, rolsuper, rolbypassrls from pg_roles "
                "where rolname in ('arrendi_api', 'arrendi_tasks') order by rolname"
            )
        ).all()

    assert [tuple(role) for role in roles] == [
        ("arrendi_api", False, False),
        ("arrendi_tasks", False, True),
    ]


@pytest.mark.parametrize("role", ["anon", "authenticated", "service_role"])
def test_supabase_data_api_roles_cannot_touch_owners(admin_engine: Engine, role: str) -> None:
    with admin_engine.connect() as connection:
        allowed = connection.execute(
            text(
                "select privilege from unnest(array['select', 'insert', 'update', 'delete']) "
                "as privilege where has_table_privilege(:role, 'owners', privilege)"
            ),
            {"role": role},
        ).scalars()

        assert allowed.all() == []


def test_models_match_the_migrations(admin_engine: Engine, admin_url: str) -> None:
    command.check(alembic_config(admin_url))
