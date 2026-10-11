"""notifications: constraints, row security and permissions."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.db import set_owner_id
from tests.conftest import Tree
from tests.test_bill_tables import insert_bill

SUPABASE_ROLES = ["anon", "authenticated", "service_role"]


def insert_notification(
    connection: Connection, owner_id: UUID, bill_id: UUID, **overrides: object
) -> UUID:
    values = {
        "id": uuid4(),
        "owner_id": owner_id,
        "bill_id": bill_id,
        "type": "bill",
        "channel": "email",
        "recipient": "arrendatario@example.com",
        "delivery_status": "pending",
    } | overrides
    connection.execute(
        text(
            "insert into notifications (id, owner_id, bill_id, type, channel, recipient, "
            "delivery_status) values (:id, :owner_id, :bill_id, :type, :channel, :recipient, "
            ":delivery_status)"
        ),
        values,
    )
    return values["id"]


@pytest.fixture
def bills(
    admin_engine: Engine, two_owners: tuple[UUID, UUID], trees: tuple[Tree, Tree]
) -> tuple[UUID, UUID]:
    """A bill with a notification for each of the two owners."""
    ids = []
    with admin_engine.begin() as connection:
        for owner, tree in zip(two_owners, trees, strict=True):
            bill_id = insert_bill(connection, owner, tree.lease_id)
            insert_notification(connection, owner, bill_id)
            ids.append(bill_id)
    return ids[0], ids[1]


def test_row_security_is_enabled_and_forced(admin_engine: Engine) -> None:
    with admin_engine.connect() as connection:
        row = connection.execute(
            text(
                "select relrowsecurity, relforcerowsecurity from pg_class "
                "where relname = 'notifications'"
            )
        ).one()

    assert tuple(row) == (True, True)


@pytest.mark.parametrize("role", SUPABASE_ROLES)
def test_supabase_data_api_roles_cannot_touch_the_table(admin_engine: Engine, role: str) -> None:
    with admin_engine.connect() as connection:
        allowed = connection.execute(
            text(
                "select privilege from unnest(array['select', 'insert', 'update', 'delete']) "
                "as privilege where has_table_privilege(:role, 'notifications', privilege)"
            ),
            {"role": role},
        ).scalars()

        assert allowed.all() == []


@pytest.mark.parametrize("role", ["arrendi_api", "arrendi_tasks"])
def test_app_roles_have_the_minimum_privileges(admin_engine: Engine, role: str) -> None:
    with admin_engine.connect() as connection:
        privileges = connection.execute(
            text(
                "select privilege from unnest(array['select', 'insert', 'update', 'delete']) "
                "as privilege where has_table_privilege(:role, 'notifications', privilege) "
                "order by privilege"
            ),
            {"role": role},
        ).scalars()

        assert privileges.all() == ["insert", "select", "update"]


def test_owner_sees_and_changes_only_their_own_rows(
    api_engine: Engine, admin_engine: Engine, two_owners: tuple[UUID, UUID], bills: tuple
) -> None:
    ana, beto = two_owners

    with api_engine.begin() as connection:
        set_owner_id(connection, ana)
        owners = connection.execute(text("select owner_id from notifications")).scalars().all()
        # No filter, so the statement reaches Beto's row if the policy lets it.
        changed = connection.execute(text("update notifications set delivery_status = 'failed'"))
    assert owners == [ana]
    assert changed.rowcount == 1

    with admin_engine.connect() as connection:
        status = connection.execute(
            text("select delivery_status from notifications where owner_id = :beto"),
            {"beto": beto},
        ).scalar_one()
    assert status == "pending"


def test_without_an_owner_no_row_is_visible(api_engine: Engine, bills: tuple) -> None:
    with api_engine.begin() as connection:
        assert connection.execute(text("select id from notifications")).all() == []


def test_owner_cannot_delete_rows(
    api_engine: Engine, two_owners: tuple[UUID, UUID], bills: tuple
) -> None:
    ana, _ = two_owners

    with pytest.raises(DBAPIError, match="permission denied"), api_engine.begin() as connection:
        set_owner_id(connection, ana)
        connection.execute(text("delete from notifications"))


def test_notification_cannot_belong_to_another_owners_bill(
    api_engine: Engine, two_owners: tuple[UUID, UUID], bills: tuple[UUID, UUID]
) -> None:
    ana, _ = two_owners
    _, betos_bill = bills

    with (
        pytest.raises(IntegrityError, match="notifications_bill_fk"),
        api_engine.begin() as connection,
    ):
        set_owner_id(connection, ana)
        insert_notification(connection, ana, betos_bill, type="resend")


def test_tasks_role_sees_every_owner(tasks_engine: Engine, bills: tuple) -> None:
    with tasks_engine.begin() as connection:
        assert connection.execute(text("select count(*) from notifications")).scalar_one() == 2


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"type": "sms"}, "notifications_type_check"),
        ({"channel": "whatsapp"}, "notifications_channel_check"),
        ({"delivery_status": "opened"}, "notifications_delivery_status_check"),
    ],
)
def test_notification_constraints(
    admin_engine: Engine,
    two_owners: tuple[UUID, UUID],
    bills: tuple[UUID, UUID],
    overrides: dict[str, object],
    constraint: str,
) -> None:
    with pytest.raises(IntegrityError, match=constraint), admin_engine.begin() as connection:
        insert_notification(connection, two_owners[0], bills[0], **overrides)


def test_automatic_emails_go_out_once_per_bill(
    admin_engine: Engine, two_owners: tuple[UUID, UUID], bills: tuple[UUID, UUID]
) -> None:
    ana, _ = two_owners

    with (
        pytest.raises(IntegrityError, match="notifications_one_automatic_per_bill"),
        admin_engine.begin() as connection,
    ):
        insert_notification(connection, ana, bills[0])

    # The other automatic ones, and as many manual ones as the owner wants.
    with admin_engine.begin() as connection:
        for kind in ("reminder_1", "reminder_2", "resend", "resend", "manual_reminder", "receipt"):
            insert_notification(connection, ana, bills[0], type=kind)
