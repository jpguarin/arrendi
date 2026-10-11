"""bills and bill_items: constraints, row security and permissions."""

from datetime import date
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.db import set_owner_id
from tests.conftest import Tree

TABLES = ["bills", "bill_items"]
SUPABASE_ROLES = ["anon", "authenticated", "service_role"]


def insert_bill(
    connection: Connection, owner_id: UUID, lease_id: UUID, **overrides: object
) -> UUID:
    values = {
        "id": uuid4(),
        "owner_id": owner_id,
        "lease_id": lease_id,
        "number": 1,
        "origin": "monthly",
        "period": date(2026, 10, 1),
        "issue_date": date(2026, 10, 1),
        "due_date": date(2026, 10, 5),
        "total": 950000,
        "status": "pending",
        "voided_at": None,
    } | overrides
    connection.execute(
        text(
            "insert into bills (id, owner_id, lease_id, number, origin, period, issue_date, "
            "due_date, total, status, pdf_path, voided_at) values (:id, :owner_id, :lease_id, "
            ":number, :origin, :period, :issue_date, :due_date, :total, :status, 'x.pdf', "
            ":voided_at)"
        ),
        values,
    )
    return values["id"]


def insert_item(
    connection: Connection, owner_id: UUID, bill_id: UUID, amount: int = 950000
) -> None:
    connection.execute(
        text(
            "insert into bill_items (owner_id, bill_id, description, amount) "
            "values (:owner_id, :bill_id, 'Canon de arrendamiento', :amount)"
        ),
        {"owner_id": owner_id, "bill_id": bill_id, "amount": amount},
    )


@pytest.fixture
def bills(
    admin_engine: Engine, two_owners: tuple[UUID, UUID], trees: tuple[Tree, Tree]
) -> tuple[UUID, UUID]:
    """A bill with its item for each of the two owners."""
    ids = []
    with admin_engine.begin() as connection:
        for owner, tree in zip(two_owners, trees, strict=True):
            bill_id = insert_bill(connection, owner, tree.lease_id)
            insert_item(connection, owner, bill_id)
            ids.append(bill_id)
    return ids[0], ids[1]


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


@pytest.mark.parametrize(
    ("table", "expected"),
    [("bills", ["insert", "select", "update"]), ("bill_items", ["insert", "select"])],
)
@pytest.mark.parametrize("role", ["arrendi_api", "arrendi_tasks"])
def test_app_roles_have_the_minimum_privileges(
    admin_engine: Engine, table: str, expected: list[str], role: str
) -> None:
    with admin_engine.connect() as connection:
        privileges = connection.execute(
            text(
                "select privilege from unnest(array['select', 'insert', 'update', 'delete']) "
                "as privilege where has_table_privilege(:role, :table, privilege) "
                "order by privilege"
            ),
            {"role": role, "table": table},
        ).scalars()

        assert privileges.all() == expected


# Isolation


@pytest.mark.parametrize("table", TABLES)
def test_owner_sees_only_their_own_rows(
    api_engine: Engine, two_owners: tuple[UUID, UUID], bills: tuple[UUID, UUID], table: str
) -> None:
    for owner in two_owners:
        with api_engine.begin() as connection:
            set_owner_id(connection, owner)
            owners = connection.execute(text(f"select owner_id from {table}")).scalars().all()
        assert owners == [owner]


@pytest.mark.parametrize("table", TABLES)
def test_without_an_owner_no_row_is_visible(
    api_engine: Engine, bills: tuple[UUID, UUID], table: str
) -> None:
    with api_engine.begin() as connection:
        assert connection.execute(text(f"select id from {table}")).all() == []


def test_owner_cannot_update_another_owners_bill(
    api_engine: Engine,
    admin_engine: Engine,
    two_owners: tuple[UUID, UUID],
    bills: tuple[UUID, UUID],
) -> None:
    ana, beto = two_owners

    with api_engine.begin() as connection:
        set_owner_id(connection, ana)
        # No filter, so the statement reaches Beto's bill if the policy lets it.
        result = connection.execute(text("update bills set status = 'paid'"))
        assert result.rowcount == 1  # only Ana's own bill

    with admin_engine.connect() as connection:
        status = connection.execute(
            text("select status from bills where owner_id = :beto"), {"beto": beto}
        ).scalar_one()
    assert status == "pending"


def test_owner_cannot_insert_a_bill_for_someone_else(
    api_engine: Engine, two_owners: tuple[UUID, UUID], trees: tuple[Tree, Tree]
) -> None:
    ana, beto = two_owners
    _, betos = trees

    with pytest.raises(DBAPIError, match="row-level security"), api_engine.begin() as connection:
        set_owner_id(connection, ana)
        insert_bill(connection, beto, betos.lease_id)


@pytest.mark.parametrize("table", TABLES)
def test_owner_cannot_delete_rows(
    api_engine: Engine, two_owners: tuple[UUID, UUID], bills: tuple[UUID, UUID], table: str
) -> None:
    ana, _ = two_owners

    with pytest.raises(DBAPIError, match="permission denied"), api_engine.begin() as connection:
        set_owner_id(connection, ana)
        connection.execute(text(f"delete from {table}"))


def test_issued_items_cannot_be_changed(
    api_engine: Engine, two_owners: tuple[UUID, UUID], bills: tuple[UUID, UUID]
) -> None:
    ana, _ = two_owners

    with pytest.raises(DBAPIError, match="permission denied"), api_engine.begin() as connection:
        set_owner_id(connection, ana)
        connection.execute(text("update bill_items set amount = 1"))


def test_tasks_role_sees_every_owner(tasks_engine: Engine, bills: tuple[UUID, UUID]) -> None:
    with tasks_engine.begin() as connection:
        assert connection.execute(text("select count(*) from bills")).scalar_one() == 2


# Rows cannot point at another owner's rows (foreign keys skip row security)


def test_bill_cannot_belong_to_another_owners_lease(
    api_engine: Engine, two_owners: tuple[UUID, UUID], trees: tuple[Tree, Tree]
) -> None:
    ana, _ = two_owners
    _, betos = trees

    with pytest.raises(IntegrityError, match="bills_lease_fk"), api_engine.begin() as connection:
        set_owner_id(connection, ana)
        insert_bill(connection, ana, betos.lease_id)


def test_item_cannot_belong_to_another_owners_bill(
    api_engine: Engine, two_owners: tuple[UUID, UUID], bills: tuple[UUID, UUID]
) -> None:
    ana, _ = two_owners
    _, betos_bill = bills

    with (
        pytest.raises(IntegrityError, match="bill_items_bill_fk"),
        api_engine.begin() as connection,
    ):
        set_owner_id(connection, ana)
        insert_item(connection, ana, betos_bill)


# Constraints


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"total": 0}, "bills_total_check"),
        ({"number": 0}, "bills_number_check"),
        ({"origin": "other"}, "bills_origin_check"),
        ({"status": "sent"}, "bills_status_check"),
        ({"period": None}, "bills_period_check"),
        ({"origin": "manual"}, "bills_period_check"),
        ({"period": date(2026, 10, 2)}, "bills_period_check"),
        ({"status": "voided"}, "bills_voided_at_check"),
    ],
)
def test_bill_constraints(
    admin_engine: Engine,
    two_owners: tuple[UUID, UUID],
    trees: tuple[Tree, Tree],
    overrides: dict[str, object],
    constraint: str,
) -> None:
    ana, _ = two_owners
    anas, _ = trees

    with pytest.raises(IntegrityError, match=constraint), admin_engine.begin() as connection:
        insert_bill(connection, ana, anas.lease_id, **overrides)


def test_item_amount_must_be_positive(admin_engine: Engine, bills: tuple[UUID, UUID]) -> None:
    anas_bill, _ = bills

    with (
        pytest.raises(IntegrityError, match="bill_items_amount_check"),
        admin_engine.begin() as connection,
    ):
        owner = connection.execute(
            text("select owner_id from bills where id = :id"), {"id": anas_bill}
        ).scalar_one()
        insert_item(connection, owner, anas_bill, amount=0)


def test_number_is_unique_per_owner(
    admin_engine: Engine, two_owners: tuple[UUID, UUID], bills: tuple[UUID, UUID], trees: tuple
) -> None:
    ana, _ = two_owners
    anas, _ = trees

    # Beto already has number 1 too: the sequence is per owner.
    with (
        pytest.raises(IntegrityError, match="bills_owner_id_number_key"),
        admin_engine.begin() as connection,
    ):
        insert_bill(connection, ana, anas.lease_id, origin="manual", period=None)


def test_one_monthly_bill_per_lease_and_period(
    admin_engine: Engine, two_owners: tuple[UUID, UUID], bills: tuple[UUID, UUID], trees: tuple
) -> None:
    ana, _ = two_owners
    anas, _ = trees

    with (
        pytest.raises(IntegrityError, match="bills_one_monthly_per_period"),
        admin_engine.begin() as connection,
    ):
        insert_bill(connection, ana, anas.lease_id, number=2)

    # Another month, a manual bill, and the same month once the first one is voided.
    with admin_engine.begin() as connection:
        insert_bill(connection, ana, anas.lease_id, number=2, period=date(2026, 11, 1))
        insert_bill(connection, ana, anas.lease_id, number=3, origin="manual", period=None)
        connection.execute(
            text("update bills set status = 'voided', voided_at = now() where id = :id"),
            {"id": bills[0]},
        )
        insert_bill(connection, ana, anas.lease_id, number=4)
