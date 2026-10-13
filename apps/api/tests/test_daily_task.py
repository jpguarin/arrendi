"""The daily task: idempotent, catches up on its own, and one failure does not stop it."""

from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.config import get_settings
from app.dates import bogota_date, today_in_bogota
from app.dependencies import get_tasks_db_engine
from app.main import app
from app.storage import StorageError
from app.tasks.daily import DailyResult, run_daily
from tests.conftest import FakeEmailSender, FakeStorage, Tree, create_tree

# The trees' leases charge $950.000, are due on the 5th and send automatically. Both
# owners send on day 1.


@pytest.fixture
def storage() -> FakeStorage:
    return FakeStorage()


@pytest.fixture
def mailer() -> FakeEmailSender:
    return FakeEmailSender()


@pytest.fixture
def run(tasks_engine: Engine, mailer: FakeEmailSender, storage: FakeStorage):
    def run_on(day: date, **kwargs: object) -> DailyResult:
        return run_daily(tasks_engine, mailer, storage, day, **kwargs)

    return run_on


def rows(admin_engine: Engine, query: str, **params: object) -> list[tuple]:
    with admin_engine.connect() as connection:
        return [tuple(row) for row in connection.execute(text(query), params)]


def execute(admin_engine: Engine, statement: str, **params: object) -> None:
    with admin_engine.begin() as connection:
        connection.execute(text(statement), params)


def bills_of(admin_engine: Engine, owner_id: UUID) -> list[tuple]:
    return rows(
        admin_engine,
        "select number, period, status from bills where owner_id = :id order by number",
        id=owner_id,
    )


def notifications_of(admin_engine: Engine, owner_id: UUID) -> list[tuple]:
    return rows(
        admin_engine,
        "select type, delivery_status from notifications where owner_id = :id "
        "order by created_at, type",
        id=owner_id,
    )


OCT = date(2026, 10, 1)


# 1. Generate


def test_generates_and_sends_the_bill_of_every_active_lease(
    run, admin_engine: Engine, two_owners: tuple[UUID, UUID], trees, mailer, storage
) -> None:
    ana, beto = two_owners

    result = run(date(2026, 10, 1))

    assert result == DailyResult(bills_generated=2, emails_sent=2)
    for owner in (ana, beto):
        assert bills_of(admin_engine, owner) == [(1, OCT, "pending")]
        assert notifications_of(admin_engine, owner) == [("bill", "sent")]
    assert sorted(message.to for message in mailer.sent) == [
        "ana@example.com",
        "beto@example.com",
    ]
    assert all(message.subject == "Cuenta de cobro N.º 0001" for message in mailer.sent)
    assert all(len(message.attachments) == 1 for message in mailer.sent)
    assert len(storage.objects) == 2


def test_bill_carries_the_leases_payment_details_and_keeps_them(
    run, admin_engine: Engine, two_owners: tuple[UUID, UUID], trees, mailer, storage
) -> None:
    ana, beto = two_owners
    execute(admin_engine, "update owners set payment_details = 'Nequi de Ajustes'")
    execute(
        admin_engine,
        "update leases set payment_details = 'Daviplata del contrato' where id = :id",
        id=trees[0].lease_id,
    )

    run(date(2026, 10, 1))

    assert rows(admin_engine, "select payment_details from bills where owner_id = :id", id=ana) == [
        ("Daviplata del contrato",)
    ]
    assert rows(
        admin_engine, "select payment_details from bills where owner_id = :id", id=beto
    ) == [("Nequi de Ajustes",)]
    by_recipient = {message.to: message.text for message in mailer.sent}
    assert "Daviplata del contrato" in by_recipient["ana@example.com"]
    assert "Nequi de Ajustes" in by_recipient["beto@example.com"]

    # The reminder says what the bill was issued with, whatever changed since.
    execute(admin_engine, "update owners set payment_details = 'Otro banco'")
    execute(admin_engine, "update leases set payment_details = null")
    mailer.sent.clear()
    run(date(2026, 10, 6))

    by_recipient = {message.to: message.text for message in mailer.sent}
    assert "Daviplata del contrato" in by_recipient["ana@example.com"]
    assert "Nequi de Ajustes" in by_recipient["beto@example.com"]
    assert all("Otro banco" not in message.text for message in mailer.sent)


def test_running_twice_the_same_day_changes_nothing(
    run, admin_engine: Engine, two_owners: tuple[UUID, UUID], trees, mailer
) -> None:
    run(date(2026, 10, 1))

    again = run(date(2026, 10, 1))

    assert again == DailyResult()
    assert bills_of(admin_engine, two_owners[0]) == [(1, OCT, "pending")]
    assert notifications_of(admin_engine, two_owners[0]) == [("bill", "sent")]
    assert len(mailer.sent) == 2


def test_waits_for_the_owners_send_day_and_catches_up_after_it(
    run, admin_engine: Engine, two_owners: tuple[UUID, UUID], trees, mailer
) -> None:
    ana, beto = two_owners
    execute(admin_engine, "update owners set send_day = 10 where id = :id", id=ana)

    early = run(date(2026, 10, 9))
    # The task did not run on the 10th or the 11th.
    late = run(date(2026, 10, 12))

    assert early.bills_generated == 1  # only Beto's
    assert late.bills_generated == 1
    # Issued on the 12th with the due date already past: born overdue.
    assert bills_of(admin_engine, ana) == [(1, OCT, "overdue")]
    assert rows(admin_engine, "select issue_date from bills where owner_id = :id", id=ana) == [
        (date(2026, 10, 12),)
    ]


def test_each_month_gets_its_own_bill(
    run, admin_engine: Engine, two_owners: tuple[UUID, UUID], trees
) -> None:
    run(date(2026, 10, 1))
    run(date(2026, 11, 1))

    assert [(number, period) for number, period, _ in bills_of(admin_engine, two_owners[0])] == [
        (1, OCT),
        (2, date(2026, 11, 1)),
    ]


def test_deposit_is_charged_on_the_first_bill_only_and_the_email_says_so(
    run, admin_engine: Engine, two_owners: tuple[UUID, UUID], trees: tuple[Tree, Tree], mailer
) -> None:
    ana, beto = two_owners
    execute(
        admin_engine,
        "update leases set deposit = 500000, charge_deposit = true where owner_id = :id",
        id=ana,
    )

    run(date(2026, 10, 1))
    run(date(2026, 10, 1))
    run(date(2026, 11, 1))

    totals = "select total from bills where owner_id = :id order by number"
    assert rows(admin_engine, totals, id=ana) == [(1450000,), (950000,)]
    assert rows(admin_engine, totals, id=beto) == [(950000,), (950000,)]
    items = (
        "select b.number, i.description, i.amount from bill_items i "
        "join bills b on b.id = i.bill_id where i.owner_id = :id order by b.number, i.position"
    )
    assert rows(admin_engine, items, id=ana) == [
        (1, "Canon de arrendamiento", 950000),
        (1, "Depósito", 500000),
        (2, "Canon de arrendamiento", 950000),
    ]
    first = next(m for m in mailer.sent if m.to == "ana@example.com")
    assert "Canon de arrendamiento y depósito · Octubre 2026 · Apto ana" in first.text
    assert "$1.450.000" in first.text


def test_bills_carry_the_items_of_their_lease(
    run, admin_engine: Engine, two_owners: tuple[UUID, UUID], trees: tuple[Tree, Tree], mailer
) -> None:
    ana, beto = two_owners
    for position, (description, amount) in enumerate(
        [("Administración", 200000), ("Parqueadero", 80000)]
    ):
        execute(
            admin_engine,
            "insert into lease_items (owner_id, lease_id, description, amount, position) "
            "values (:owner, :lease, :description, :amount, :position)",
            owner=ana,
            lease=trees[0].lease_id,
            description=description,
            amount=amount,
            position=position,
        )

    run(date(2026, 10, 1))
    run(date(2026, 10, 1))

    totals = "select total from bills where owner_id = :id order by number"
    assert rows(admin_engine, totals, id=ana) == [(1230000,)]
    assert rows(admin_engine, totals, id=beto) == [(950000,)]
    items = "select description, amount from bill_items where owner_id = :id order by position"
    assert rows(admin_engine, items, id=ana) == [
        ("Canon de arrendamiento", 950000),
        ("Administración", 200000),
        ("Parqueadero", 80000),
    ]
    assert rows(admin_engine, items, id=beto) == [("Canon de arrendamiento", 950000)]
    (first,) = [m for m in mailer.sent if m.to == "ana@example.com"]
    assert (
        "Canon de arrendamiento, administración y parqueadero · Octubre 2026 · Apto ana"
        in first.text
    )
    assert "$1.230.000" in first.text


def test_lease_without_automatic_sending_gets_its_bill_but_no_email(
    run, admin_engine: Engine, two_owners: tuple[UUID, UUID], trees: tuple[Tree, Tree], mailer
) -> None:
    ana, _ = two_owners
    execute(admin_engine, "update leases set auto_send = false where owner_id = :id", id=ana)

    run(date(2026, 10, 1))
    # Weeks later it is overdue, but the tenant never got it: no reminders either.
    run(date(2026, 10, 20))

    assert bills_of(admin_engine, ana) == [(1, OCT, "overdue")]
    assert notifications_of(admin_engine, ana) == []
    assert "ana@example.com" not in {message.to for message in mailer.sent}


def test_ended_lease_gets_no_bill(
    run, admin_engine: Engine, two_owners: tuple[UUID, UUID], trees
) -> None:
    ana, _ = two_owners
    execute(admin_engine, "update leases set status = 'ended' where owner_id = :id", id=ana)

    assert run(date(2026, 10, 1)).bills_generated == 1
    assert bills_of(admin_engine, ana) == []


def test_bill_issued_by_hand_is_not_issued_again_but_a_voided_one_is_replaced(
    run, admin_engine: Engine, two_owners: tuple[UUID, UUID], trees
) -> None:
    ana, _ = two_owners
    run(date(2026, 10, 1))
    execute(
        admin_engine,
        "update bills set status = 'voided', voided_at = now() where owner_id = :id",
        id=ana,
    )

    result = run(date(2026, 10, 2))

    assert result.bills_generated == 1
    assert bills_of(admin_engine, ana) == [(1, OCT, "voided"), (2, OCT, "pending")]


class FlakyStorage(FakeStorage):
    """Fails the first upload, like a storage hiccup in the middle of the task."""

    def __init__(self) -> None:
        super().__init__()
        self.failures = 1

    def upload(self, path: str, content: bytes, content_type: str = "") -> None:
        if self.failures:
            self.failures -= 1
            raise StorageError("storage hiccup")
        super().upload(path, content, content_type)


def test_one_failing_lease_does_not_stop_the_rest(
    tasks_engine: Engine,
    admin_engine: Engine,
    two_owners: tuple[UUID, UUID],
    trees: tuple[Tree, Tree],
    mailer: FakeEmailSender,
) -> None:
    ana, beto = two_owners
    with admin_engine.begin() as connection:
        create_tree(connection, ana, "extra")
    storage = FlakyStorage()

    first = run_daily(tasks_engine, mailer, storage, date(2026, 10, 1))
    second = run_daily(tasks_engine, mailer, storage, date(2026, 10, 1))

    assert (first.bills_generated, first.emails_sent, first.errors) == (2, 2, 1)
    # The next run issues the one that failed, and the numbers have no gap.
    assert (second.bills_generated, second.emails_sent, second.errors) == (1, 1, 0)
    assert [number for number, _, _ in bills_of(admin_engine, ana)] == [1, 2]
    assert [number for number, _, _ in bills_of(admin_engine, beto)] == [1]
    assert len(mailer.sent) == 3


def test_email_that_failed_is_sent_by_the_next_run(
    run, admin_engine: Engine, two_owners: tuple[UUID, UUID], trees, mailer
) -> None:
    ana, _ = two_owners
    mailer.failing = True
    failed = run(date(2026, 10, 1))
    assert (failed.bills_generated, failed.emails_sent, failed.errors) == (2, 0, 2)
    assert notifications_of(admin_engine, ana) == [("bill", "failed")]

    mailer.failing = False
    retried = run(date(2026, 10, 2))

    assert (retried.bills_generated, retried.emails_sent, retried.errors) == (0, 2, 0)
    assert notifications_of(admin_engine, ana) == [("bill", "sent")]
    assert len(mailer.sent) == 2


def test_out_of_time_stops_and_says_so(run, admin_engine: Engine, two_owners, trees) -> None:
    result = run(date(2026, 10, 1), deadline=0.0)

    assert (result.bills_generated, result.finished) == (0, False)
    # The next run, with time, does the work.
    assert run(date(2026, 10, 1)).bills_generated == 2


# 2. Mark overdue


def test_bills_become_overdue_the_day_after_they_are_due(
    run, admin_engine: Engine, two_owners: tuple[UUID, UUID], trees
) -> None:
    ana, _ = two_owners
    run(date(2026, 10, 1))

    on_due_date = run(date(2026, 10, 5))
    assert on_due_date.bills_marked_overdue == 0
    assert bills_of(admin_engine, ana) == [(1, OCT, "pending")]

    next_day = run(date(2026, 10, 6))
    assert next_day.bills_marked_overdue == 2
    assert bills_of(admin_engine, ana) == [(1, OCT, "overdue")]


def test_paid_and_voided_bills_are_left_alone_and_partial_ones_become_overdue(
    run, admin_engine: Engine, two_owners: tuple[UUID, UUID], trees
) -> None:
    ana, beto = two_owners
    run(date(2026, 10, 1))
    execute(admin_engine, "update bills set status = 'paid' where owner_id = :id", id=ana)
    execute(admin_engine, "update bills set status = 'partial' where owner_id = :id", id=beto)

    result = run(date(2026, 10, 6))

    assert result.bills_marked_overdue == 1
    assert bills_of(admin_engine, ana) == [(1, OCT, "paid")]
    assert bills_of(admin_engine, beto) == [(1, OCT, "overdue")]
    # A paid bill gets no reminder.
    assert notifications_of(admin_engine, ana) == [("bill", "sent")]


# 3. Remind


def test_first_reminder_goes_out_once_the_day_after_the_due_date(
    run, admin_engine: Engine, two_owners: tuple[UUID, UUID], trees, mailer
) -> None:
    ana, _ = two_owners
    run(date(2026, 10, 1))
    run(date(2026, 10, 5))
    assert notifications_of(admin_engine, ana) == [("bill", "sent")]

    first = run(date(2026, 10, 6))
    again = run(date(2026, 10, 6))
    next_day = run(date(2026, 10, 7))

    assert first.emails_sent == 2
    assert (again.emails_sent, next_day.emails_sent) == (0, 0)
    assert notifications_of(admin_engine, ana) == [("bill", "sent"), ("reminder_1", "sent")]
    reminder = next(
        m for m in mailer.sent if m.to == "ana@example.com" and "Recordatorio" in m.subject
    )
    assert reminder.subject == "Recordatorio: cuenta de cobro N.º 0001 pendiente"
    assert "Saldo pendiente: $950.000" in reminder.text


def test_second_reminder_goes_out_seven_days_after_the_due_date(
    run, admin_engine: Engine, two_owners: tuple[UUID, UUID], trees, mailer
) -> None:
    ana, _ = two_owners
    run(date(2026, 10, 1))
    run(date(2026, 10, 6))

    assert run(date(2026, 10, 11)).emails_sent == 0
    assert run(date(2026, 10, 12)).emails_sent == 2
    assert run(date(2026, 10, 13)).emails_sent == 0

    assert notifications_of(admin_engine, ana) == [
        ("bill", "sent"),
        ("reminder_1", "sent"),
        ("reminder_2", "sent"),
    ]
    assert any("7 días de atraso" in message.subject for message in mailer.sent)


def test_after_lost_days_reminders_go_out_one_per_run(
    run, admin_engine: Engine, two_owners: tuple[UUID, UUID], trees
) -> None:
    ana, _ = two_owners
    run(date(2026, 10, 1))

    # Nothing ran for two weeks.
    first = run(date(2026, 10, 15))
    assert first.emails_sent == 2
    assert notifications_of(admin_engine, ana) == [("bill", "sent"), ("reminder_1", "sent")]

    second = run(date(2026, 10, 16))
    assert second.emails_sent == 2
    assert notifications_of(admin_engine, ana)[-1] == ("reminder_2", "sent")


def test_owner_can_turn_each_reminder_off(
    run, admin_engine: Engine, two_owners: tuple[UUID, UUID], trees
) -> None:
    ana, beto = two_owners
    execute(admin_engine, "update owners set reminder_1 = false where id = :id", id=ana)
    execute(admin_engine, "update owners set reminder_2 = false where id = :id", id=beto)
    run(date(2026, 10, 1))

    run(date(2026, 10, 6))
    run(date(2026, 10, 12))

    assert notifications_of(admin_engine, ana) == [("bill", "sent"), ("reminder_2", "sent")]
    assert notifications_of(admin_engine, beto) == [("bill", "sent"), ("reminder_1", "sent")]


def test_bill_sent_by_hand_gets_its_reminders(
    run, admin_engine: Engine, two_owners: tuple[UUID, UUID], trees
) -> None:
    ana, _ = two_owners
    execute(admin_engine, "update leases set auto_send = false where owner_id = :id", id=ana)
    run(date(2026, 10, 1))
    # The owner sent it from the app.
    execute(
        admin_engine,
        "insert into notifications (owner_id, bill_id, type, recipient, delivery_status) "
        "select owner_id, id, 'bill', 'ana@example.com', 'sent' from bills where owner_id = :id",
        id=ana,
    )

    run(date(2026, 10, 6))

    assert ("reminder_1", "sent") in notifications_of(admin_engine, ana)


# "Today" is the day in Colombia


def test_business_date_is_the_day_in_colombia_not_in_utc() -> None:
    # 03:00 UTC on the 6th is still 10 p. m. on the 5th in Bogotá.
    assert bogota_date(datetime(2026, 10, 6, 3, 0, tzinfo=UTC)) == date(2026, 10, 5)
    assert bogota_date(datetime(2026, 10, 6, 5, 0, tzinfo=UTC)) == date(2026, 10, 6)
    # The cron fires at 11:00 UTC: 6 a. m. the same day.
    assert bogota_date(datetime(2026, 10, 1, 11, 0, tzinfo=UTC)) == date(2026, 10, 1)


# The route the Cron Job calls


@pytest.fixture
def cron(api: TestClient, tasks_engine: Engine, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    from app.dependencies import get_email_sender, get_storage

    monkeypatch.setattr(get_settings(), "cron_secret", "s3cret-for-the-cron-job")
    app.dependency_overrides[get_tasks_db_engine] = lambda: tasks_engine
    app.dependency_overrides[get_storage] = lambda: FakeStorage()
    app.dependency_overrides[get_email_sender] = lambda: FakeEmailSender()
    app.dependency_overrides[today_in_bogota] = lambda: date(2026, 10, 1)
    return api


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer wrong"},
        {"Authorization": "s3cret-for-the-cron-job"},
        {"Authorization": "Bearer "},
    ],
)
def test_cron_route_needs_the_secret(
    cron: TestClient, admin_engine: Engine, two_owners, trees, headers: dict[str, str]
) -> None:
    response = cron.get("/api/cron/daily", headers=headers)

    assert response.status_code == 401
    assert bills_of(admin_engine, two_owners[0]) == []


def test_cron_route_lets_nobody_in_when_no_secret_is_configured(
    cron: TestClient, monkeypatch: pytest.MonkeyPatch, admin_engine: Engine, two_owners, trees
) -> None:
    monkeypatch.setattr(get_settings(), "cron_secret", "")

    response = cron.get("/api/cron/daily", headers={"Authorization": "Bearer "})

    assert response.status_code == 401
    assert bills_of(admin_engine, two_owners[0]) == []


def test_cron_route_runs_the_task_and_reports(
    cron: TestClient, admin_engine: Engine, two_owners, trees
) -> None:
    headers = {"Authorization": "Bearer s3cret-for-the-cron-job"}

    first = cron.get("/api/cron/daily", headers=headers)
    second = cron.get("/api/cron/daily", headers=headers)

    assert first.status_code == 200
    assert first.json() == {
        "bills_generated": 2,
        "bills_marked_overdue": 0,
        "emails_sent": 2,
        "errors": 0,
        "finished": True,
    }
    assert second.json()["bills_generated"] == 0
    assert bills_of(admin_engine, two_owners[0]) == [(1, OCT, "pending")]
