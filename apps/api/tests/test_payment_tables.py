"""payments: constraints, row security and permissions."""

from datetime import date
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.db import set_owner_id
from tests.conftest import Tree
from tests.test_bill_tables import insert_bill

SUPABASE_ROLES = ["anon", "authenticated", "service_role"]


def insert_payment(
    connection: Connection, owner_id: UUID, bill_id: UUID, **overrides: object
) -> UUID:
    values = {
        "id": uuid4(),
        "owner_id": owner_id,
        "bill_id": bill_id,
        "payment_date": date(2026, 10, 3),
        "amount": 400000,
        "method": "transfer",
    } | overrides
    connection.execute(
        text(
            "insert into payments (id, owner_id, bill_id, payment_date, amount, method) "
            "values (:id, :owner_id, :bill_id, :payment_date, :amount, :method)"
        ),
        values,
    )
    return values["id"]


@pytest.fixture
def bills(
    admin_engine: Engine, two_owners: tuple[UUID, UUID], trees: tuple[Tree, Tree]
) -> tuple[UUID, UUID]:
    """A bill with a payment for each of the two owners."""
    ids = []
    with admin_engine.begin() as connection:
        for owner, tree in zip(two_owners, trees, strict=True):
            bill_id = insert_bill(connection, owner, tree.lease_id)
            insert_payment(connection, owner, bill_id)
            ids.append(bill_id)
    return ids[0], ids[1]


def test_row_security_is_enabled_and_forced(admin_engine: Engine) -> None:
    with admin_engine.connect() as connection:
        row = connection.execute(
            text(
                "select relrowsecurity, relforcerowsecurity from pg_class "
                "where relname = 'payments'"
            )
        ).one()

    assert tuple(row) == (True, True)


@pytest.mark.parametrize("role", SUPABASE_ROLES)
def test_supabase_data_api_roles_cannot_touch_the_table(admin_engine: Engine, role: str) -> None:
    with admin_engine.connect() as connection:
        allowed = connection.execute(
            text(
                "select privilege from unnest(array['select', 'insert', 'update', 'delete']) "
                "as privilege where has_table_privilege(:role, 'payments', privilege)"
            ),
            {"role": role},
        ).scalars()

        assert allowed.all() == []


@pytest.mark.parametrize(
    ("role", "expected"),
    [("arrendi_api", ["delete", "insert", "select", "update"]), ("arrendi_tasks", ["select"])],
)
def test_app_roles_have_the_minimum_privileges(
    admin_engine: Engine, role: str, expected: list[str]
) -> None:
    with admin_engine.connect() as connection:
        privileges = connection.execute(
            text(
                "select privilege from unnest(array['select', 'insert', 'update', 'delete']) "
                "as privilege where has_table_privilege(:role, 'payments', privilege) "
                "order by privilege"
            ),
            {"role": role},
        ).scalars()

        assert privileges.all() == expected


def test_owner_sees_changes_and_deletes_only_their_own_rows(
    api_engine: Engine, admin_engine: Engine, two_owners: tuple[UUID, UUID], bills: tuple
) -> None:
    ana, beto = two_owners

    with api_engine.begin() as connection:
        set_owner_id(connection, ana)
        owners = connection.execute(text("select owner_id from payments")).scalars().all()
        # No filter, so each statement reaches Beto's row if the policy lets it.
        changed = connection.execute(text("update payments set amount = 1"))
        deleted = connection.execute(text("delete from payments"))
    assert owners == [ana]
    assert (changed.rowcount, deleted.rowcount) == (1, 1)

    with admin_engine.connect() as connection:
        left = connection.execute(text("select owner_id, amount from payments")).all()
    assert [tuple(row) for row in left] == [(beto, 400000)]


def test_without_an_owner_no_row_is_visible(api_engine: Engine, bills: tuple) -> None:
    with api_engine.begin() as connection:
        assert connection.execute(text("select id from payments")).all() == []


def test_owner_cannot_insert_a_payment_for_someone_else(
    api_engine: Engine, two_owners: tuple[UUID, UUID], bills: tuple[UUID, UUID]
) -> None:
    ana, beto = two_owners

    with pytest.raises(DBAPIError, match="row-level security"), api_engine.begin() as connection:
        set_owner_id(connection, ana)
        insert_payment(connection, beto, bills[1])


def test_payment_cannot_belong_to_another_owners_bill(
    api_engine: Engine, two_owners: tuple[UUID, UUID], bills: tuple[UUID, UUID]
) -> None:
    ana, _ = two_owners

    with pytest.raises(IntegrityError, match="payments_bill_fk"), api_engine.begin() as connection:
        set_owner_id(connection, ana)
        insert_payment(connection, ana, bills[1])


def test_tasks_role_reads_every_owner_but_cannot_change_payments(
    tasks_engine: Engine, bills: tuple
) -> None:
    with tasks_engine.begin() as connection:
        assert connection.execute(text("select count(*) from payments")).scalar_one() == 2

    with pytest.raises(DBAPIError, match="permission denied"), tasks_engine.begin() as connection:
        connection.execute(text("delete from payments"))


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"amount": 0}, "payments_amount_check"),
        ({"amount": -5}, "payments_amount_check"),
        ({"method": "card"}, "payments_method_check"),
    ],
)
def test_payment_constraints(
    admin_engine: Engine,
    two_owners: tuple[UUID, UUID],
    bills: tuple[UUID, UUID],
    overrides: dict[str, object],
    constraint: str,
) -> None:
    with pytest.raises(IntegrityError, match=constraint), admin_engine.begin() as connection:
        insert_payment(connection, two_owners[0], bills[0], **overrides)
