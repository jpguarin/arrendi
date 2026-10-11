"""properties, units, tenants and leases: constraints, row security and permissions."""

from datetime import date
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.db import set_owner_id
from tests.conftest import Tree

TABLES = ["properties", "units", "tenants", "leases"]
SUPABASE_ROLES = ["anon", "authenticated", "service_role"]


def insert_lease(connection, owner_id: UUID, tree: Tree, **overrides: object) -> None:
    values = {
        "id": uuid4(),
        "owner_id": owner_id,
        "unit_id": tree.unit_id,
        "tenant_id": tree.tenant_id,
        "rent": 950000,
        "due_day": 5,
        "start_date": date(2026, 1, 1),
        "end_date": None,
        "deposit": None,
        "status": "active",
    } | overrides
    connection.execute(
        text(
            "insert into leases (id, owner_id, unit_id, tenant_id, rent, due_day, "
            "start_date, end_date, deposit, status) values (:id, :owner_id, :unit_id, "
            ":tenant_id, :rent, :due_day, :start_date, :end_date, :deposit, :status)"
        ),
        values,
    )


# Row security and permissions


@pytest.mark.parametrize("table", TABLES)
def test_row_security_is_enabled_and_forced(admin_engine: Engine, table: str) -> None:
    with admin_engine.connect() as connection:
        row = connection.execute(
            text("select relrowsecurity, relforcerowsecurity from pg_class where relname = :t"),
            {"t": table},
        ).one()

    assert tuple(row) == (True, True)


@pytest.mark.parametrize("table", TABLES)
@pytest.mark.parametrize("role", SUPABASE_ROLES)
def test_supabase_data_api_roles_cannot_touch_the_table(
    admin_engine: Engine, table: str, role: str
) -> None:
    with admin_engine.connect() as connection:
        allowed = connection.execute(
            text(
                "select privilege from unnest(array['select', 'insert', 'update', 'delete']) "
                "as privilege where has_table_privilege(:role, :table, privilege)"
            ),
            {"role": role, "table": table},
        ).scalars()

        assert allowed.all() == []


@pytest.mark.parametrize("table", TABLES)
def test_app_roles_have_the_minimum_privileges(admin_engine: Engine, table: str) -> None:
    with admin_engine.connect() as connection:
        privileges = {
            role: connection.execute(
                text(
                    "select privilege from unnest(array['select', 'insert', 'update', 'delete']) "
                    "as privilege where has_table_privilege(:role, :table, privilege) "
                    "order by privilege"
                ),
                {"role": role, "table": table},
            )
            .scalars()
            .all()
            for role in ("arrendi_api", "arrendi_tasks")
        }

    assert privileges == {
        "arrendi_api": ["insert", "select", "update"],
        "arrendi_tasks": ["select"],
    }


# Isolation


@pytest.mark.parametrize("table", TABLES)
def test_owner_sees_only_their_own_rows(
    api_engine: Engine, two_owners: tuple[UUID, UUID], trees: tuple[Tree, Tree], table: str
) -> None:
    ana, beto = two_owners

    for owner in (ana, beto):
        with api_engine.begin() as connection:
            set_owner_id(connection, owner)
            owners = connection.execute(text(f"select owner_id from {table}")).scalars().all()
        assert owners == [owner]


@pytest.mark.parametrize("table", TABLES)
def test_without_an_owner_no_row_is_visible(
    api_engine: Engine, trees: tuple[Tree, Tree], table: str
) -> None:
    with api_engine.begin() as connection:
        assert connection.execute(text(f"select id from {table}")).all() == []


@pytest.mark.parametrize(
    ("table", "column", "value"),
    [
        ("properties", "name", "Hackeada"),
        ("units", "name", "Hackeada"),
        ("tenants", "name", "Hackeado"),
        ("leases", "rent", 1),
    ],
)
def test_owner_cannot_update_another_owners_rows(
    api_engine: Engine,
    admin_engine: Engine,
    two_owners: tuple[UUID, UUID],
    trees: tuple[Tree, Tree],
    table: str,
    column: str,
    value: object,
) -> None:
    ana, beto = two_owners

    with api_engine.begin() as connection:
        set_owner_id(connection, ana)
        # No filter, so the statement reaches Beto's rows if the policy lets it.
        result = connection.execute(text(f"update {table} set {column} = :value"), {"value": value})
        assert result.rowcount == 1  # only Ana's own row

    with admin_engine.connect() as connection:
        changed = connection.execute(
            text(
                f"select count(*) from {table} where owner_id = :beto and {column}::text = :value"
            ),
            {"beto": beto, "value": str(value)},
        ).scalar_one()
    assert changed == 0


def test_owner_cannot_insert_a_property_for_someone_else(
    api_engine: Engine, two_owners: tuple[UUID, UUID]
) -> None:
    ana, beto = two_owners

    with pytest.raises(DBAPIError, match="row-level security"), api_engine.begin() as connection:
        set_owner_id(connection, ana)
        connection.execute(
            text("insert into properties (owner_id, name, type) values (:o, 'X', 'house')"),
            {"o": beto},
        )


def test_owner_cannot_hand_a_row_to_someone_else(
    api_engine: Engine, two_owners: tuple[UUID, UUID], trees: tuple[Tree, Tree]
) -> None:
    ana, beto = two_owners

    with pytest.raises(DBAPIError, match="row-level security"), api_engine.begin() as connection:
        set_owner_id(connection, ana)
        connection.execute(text("update tenants set owner_id = :beto"), {"beto": beto})


@pytest.mark.parametrize("table", TABLES)
def test_owner_cannot_delete_rows(
    api_engine: Engine, two_owners: tuple[UUID, UUID], trees: tuple[Tree, Tree], table: str
) -> None:
    ana, _ = two_owners

    with pytest.raises(DBAPIError, match="permission denied"), api_engine.begin() as connection:
        set_owner_id(connection, ana)
        connection.execute(text(f"delete from {table}"))


def test_tasks_role_sees_every_owner(tasks_engine: Engine, trees: tuple[Tree, Tree]) -> None:
    with tasks_engine.begin() as connection:
        assert connection.execute(text("select count(*) from leases")).scalar_one() == 2


# Rows cannot point at another owner's rows (foreign keys skip row security)


def test_unit_cannot_belong_to_another_owners_property(
    api_engine: Engine, two_owners: tuple[UUID, UUID], trees: tuple[Tree, Tree]
) -> None:
    ana, _ = two_owners
    _, betos = trees

    with pytest.raises(IntegrityError, match="units_property_fk"), api_engine.begin() as conn:
        set_owner_id(conn, ana)
        conn.execute(
            text(
                "insert into units (owner_id, property_id, name, use) "
                "values (:owner, :property, 'Colada', 'residential')"
            ),
            {"owner": ana, "property": betos.property_id},
        )


def test_lease_cannot_use_another_owners_unit(
    api_engine: Engine,
    admin_engine: Engine,
    two_owners: tuple[UUID, UUID],
    trees: tuple[Tree, Tree],
) -> None:
    ana, _ = two_owners
    anas, betos = trees
    # Free Beto's unit, so the foreign key is what stops Ana and not the one-active rule.
    with admin_engine.begin() as connection:
        connection.execute(
            text("update leases set status = 'ended' where id = :id"), {"id": betos.lease_id}
        )

    with pytest.raises(IntegrityError, match="leases_unit_fk"), api_engine.begin() as conn:
        set_owner_id(conn, ana)
        insert_lease(conn, ana, Tree(betos.property_id, betos.unit_id, anas.tenant_id, uuid4()))


def test_lease_cannot_use_another_owners_tenant(
    api_engine: Engine, two_owners: tuple[UUID, UUID], trees: tuple[Tree, Tree]
) -> None:
    ana, _ = two_owners
    anas, betos = trees

    with pytest.raises(IntegrityError, match="leases_tenant_fk"), api_engine.begin() as conn:
        set_owner_id(conn, ana)
        # Her own unit is taken, so end her lease first to reach the tenant check.
        conn.execute(text("update leases set status = 'ended'"))
        insert_lease(
            conn, ana, Tree(anas.property_id, anas.unit_id, betos.tenant_id, anas.lease_id)
        )


# Constraints


def test_property_type_must_be_a_known_one(
    api_engine: Engine, two_owners: tuple[UUID, UUID]
) -> None:
    ana, _ = two_owners

    with pytest.raises(IntegrityError, match="properties_type_check"), api_engine.begin() as conn:
        set_owner_id(conn, ana)
        conn.execute(
            text("insert into properties (owner_id, name, type) values (:o, 'X', 'castle')"),
            {"o": ana},
        )


def test_unit_use_must_be_a_known_one(
    api_engine: Engine, two_owners: tuple[UUID, UUID], trees: tuple[Tree, Tree]
) -> None:
    ana, _ = two_owners
    anas, _ = trees

    with pytest.raises(IntegrityError, match="units_use_check"), api_engine.begin() as conn:
        set_owner_id(conn, ana)
        conn.execute(
            text(
                "insert into units (owner_id, property_id, name, use) "
                "values (:o, :p, 'X', 'industrial')"
            ),
            {"o": ana, "p": anas.property_id},
        )


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"rent": 0}, "leases_rent_check"),
        ({"rent": -1}, "leases_rent_check"),
        ({"due_day": 0}, "leases_due_day_check"),
        ({"due_day": 29}, "leases_due_day_check"),
        ({"end_date": date(2026, 1, 1)}, "leases_dates_check"),
        ({"end_date": date(2025, 12, 31)}, "leases_dates_check"),
        ({"deposit": -1}, "leases_deposit_check"),
        ({"status": "paused"}, "leases_status_check"),
    ],
)
def test_lease_values_are_validated(
    api_engine: Engine,
    two_owners: tuple[UUID, UUID],
    trees: tuple[Tree, Tree],
    overrides: dict[str, object],
    constraint: str,
) -> None:
    ana, _ = two_owners
    anas, _ = trees

    with pytest.raises(IntegrityError, match=constraint), api_engine.begin() as conn:
        set_owner_id(conn, ana)
        conn.execute(text("update leases set status = 'ended'"))
        insert_lease(conn, ana, anas, **overrides)


def test_a_unit_has_at_most_one_active_lease(
    api_engine: Engine, two_owners: tuple[UUID, UUID], trees: tuple[Tree, Tree]
) -> None:
    ana, _ = two_owners
    anas, _ = trees

    with (
        pytest.raises(IntegrityError, match="leases_one_active_per_unit"),
        api_engine.begin() as conn,
    ):
        set_owner_id(conn, ana)
        insert_lease(conn, ana, anas)


def test_a_unit_can_have_many_ended_leases_and_one_active(
    api_engine: Engine, two_owners: tuple[UUID, UUID], trees: tuple[Tree, Tree]
) -> None:
    ana, _ = two_owners
    anas, _ = trees

    with api_engine.begin() as conn:
        set_owner_id(conn, ana)
        conn.execute(text("update leases set status = 'ended'"))
        insert_lease(conn, ana, anas, status="ended")
        insert_lease(conn, ana, anas, status="active")
        statuses = conn.execute(text("select status from leases order by status")).scalars().all()

    assert statuses == ["active", "ended", "ended"]


def test_updated_at_changes_on_update(
    api_engine: Engine, two_owners: tuple[UUID, UUID], trees: tuple[Tree, Tree]
) -> None:
    ana, _ = two_owners

    with api_engine.begin() as conn:
        set_owner_id(conn, ana)
        conn.execute(text("update leases set rent = 1000000"))
        row = conn.execute(text("select created_at, updated_at from leases")).one()

    assert row.updated_at > row.created_at
