"""lease_items: constraints, row security and permissions."""

from uuid import UUID

import pytest
from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.db import set_owner_id
from tests.conftest import Tree

SUPABASE_ROLES = ["anon", "authenticated", "service_role"]


def insert_item(
    connection: Connection, owner_id: UUID, lease_id: UUID, **overrides: object
) -> None:
    values = {
        "owner_id": owner_id,
        "lease_id": lease_id,
        "description": "Administración",
        "amount": 200000,
        "position": 0,
    } | overrides
    connection.execute(
        text(
            "insert into lease_items (owner_id, lease_id, description, amount, position) "
            "values (:owner_id, :lease_id, :description, :amount, :position)"
        ),
        values,
    )


@pytest.fixture
def items(admin_engine: Engine, two_owners: tuple[UUID, UUID], trees: tuple[Tree, Tree]) -> None:
    """An item on the lease of each of the two owners."""
    with admin_engine.begin() as connection:
        for owner, tree in zip(two_owners, trees, strict=True):
            insert_item(connection, owner, tree.lease_id)


def test_row_security_is_enabled_and_forced(admin_engine: Engine) -> None:
    with admin_engine.connect() as connection:
        row = connection.execute(
            text(
                "select relrowsecurity, relforcerowsecurity from pg_class "
                "where relname = 'lease_items'"
            )
        ).one()

    assert tuple(row) == (True, True)


@pytest.mark.parametrize("role", SUPABASE_ROLES)
def test_supabase_data_api_roles_cannot_touch_the_table(admin_engine: Engine, role: str) -> None:
    with admin_engine.connect() as connection:
        allowed = connection.execute(
            text(
                "select privilege from unnest(array['select', 'insert', 'update', 'delete']) "
                "as privilege where has_table_privilege(:role, 'lease_items', privilege)"
            ),
            {"role": role},
        ).scalars()

        assert allowed.all() == []


@pytest.mark.parametrize(
    ("role", "expected"),
    # The API replaces the list of a lease: it deletes and inserts, and never updates.
    [("arrendi_api", ["delete", "insert", "select"]), ("arrendi_tasks", ["select"])],
)
def test_app_roles_have_the_minimum_privileges(
    admin_engine: Engine, role: str, expected: list[str]
) -> None:
    with admin_engine.connect() as connection:
        privileges = connection.execute(
            text(
                "select privilege from unnest(array['select', 'insert', 'update', 'delete']) "
                "as privilege where has_table_privilege(:role, 'lease_items', privilege) "
                "order by privilege"
            ),
            {"role": role},
        ).scalars()

        assert privileges.all() == expected


def test_owner_sees_and_deletes_only_their_own_rows(
    api_engine: Engine, admin_engine: Engine, two_owners: tuple[UUID, UUID], items: None
) -> None:
    ana, beto = two_owners

    with api_engine.begin() as connection:
        set_owner_id(connection, ana)
        owners = connection.execute(text("select owner_id from lease_items")).scalars().all()
        # No filter, so it reaches Beto's row if the policy lets it.
        deleted = connection.execute(text("delete from lease_items"))
    assert owners == [ana]
    assert deleted.rowcount == 1

    with admin_engine.connect() as connection:
        left = connection.execute(text("select owner_id from lease_items")).scalars().all()
    assert left == [beto]


def test_without_an_owner_no_row_is_visible(api_engine: Engine, items: None) -> None:
    with api_engine.begin() as connection:
        assert connection.execute(text("select id from lease_items")).all() == []


def test_owner_cannot_insert_an_item_for_someone_else(
    api_engine: Engine, two_owners: tuple[UUID, UUID], trees: tuple[Tree, Tree]
) -> None:
    ana, beto = two_owners

    with pytest.raises(DBAPIError, match="row-level security"), api_engine.begin() as connection:
        set_owner_id(connection, ana)
        insert_item(connection, beto, trees[1].lease_id)


def test_item_cannot_belong_to_another_owners_lease(
    api_engine: Engine, two_owners: tuple[UUID, UUID], trees: tuple[Tree, Tree]
) -> None:
    ana, _ = two_owners

    with (
        pytest.raises(IntegrityError, match="lease_items_lease_fk"),
        api_engine.begin() as connection,
    ):
        set_owner_id(connection, ana)
        insert_item(connection, ana, trees[1].lease_id)


def test_tasks_role_reads_every_owner_but_cannot_change_items(
    tasks_engine: Engine, items: None
) -> None:
    with tasks_engine.begin() as connection:
        assert connection.execute(text("select count(*) from lease_items")).scalar_one() == 2

    with pytest.raises(DBAPIError, match="permission denied"), tasks_engine.begin() as connection:
        connection.execute(text("delete from lease_items"))


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"amount": 0}, "lease_items_amount_check"),
        ({"amount": -5}, "lease_items_amount_check"),
        ({"position": -1}, "lease_items_position_check"),
    ],
)
def test_item_constraints(
    admin_engine: Engine,
    two_owners: tuple[UUID, UUID],
    trees: tuple[Tree, Tree],
    overrides: dict[str, object],
    constraint: str,
) -> None:
    with pytest.raises(IntegrityError, match=constraint), admin_engine.begin() as connection:
        insert_item(connection, two_owners[0], trees[0].lease_id, **overrides)


def test_two_items_of_a_lease_cannot_share_a_position(
    admin_engine: Engine, two_owners: tuple[UUID, UUID], trees: tuple[Tree, Tree], items: None
) -> None:
    with (
        pytest.raises(IntegrityError, match="lease_items_lease_id_position_key"),
        admin_engine.begin() as connection,
    ):
        insert_item(connection, two_owners[0], trees[0].lease_id)
