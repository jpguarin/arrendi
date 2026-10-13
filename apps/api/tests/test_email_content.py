from dataclasses import replace
from datetime import date

import pytest

from app.email.content import KINDS, BillEmail, render_email

TODAY = date(2026, 10, 13)
EMAIL = BillEmail(
    owner_name="Ana Gómez",
    tenant_name="Carlos Rojas",
    number=31,
    concept="Canon de arrendamiento · Octubre 2026 · Apto 2",
    total=1_000_000,
    balance=600_000,
    due_date=date(2026, 10, 5),
    payment_details="Bancolombia, ahorros 123-456789-00\nNequi 300 123 4567",
    payment_amount=400_000,
    payment_date=date(2026, 10, 12),
    payment_method="Transferencia",
)


@pytest.mark.parametrize("kind", KINDS)
def test_every_email_has_both_versions_and_says_who_it_is_from(kind: str) -> None:
    email = render_email(kind, EMAIL, TODAY)

    assert "N.º 0031" in email.subject
    for body in (email.html, email.text):
        assert "Hola, Carlos Rojas:" in body
        assert "Ana Gómez" in body
        assert "Cuenta de cobro N.º 0031" in body
        assert "Octubre 2026 · Apto 2" in body
    assert email.html.startswith("<!doctype html>")
    assert "<" not in email.text


def test_bill_says_period_amount_due_date_and_how_to_pay() -> None:
    email = render_email("bill", EMAIL, date(2026, 10, 1))

    assert email.subject == "Cuenta de cobro N.º 0031"
    for body in (email.html, email.text):
        assert "canon de arrendamiento · Octubre 2026 · Apto 2" in body
        assert "$1.000.000" in body
        assert "Vence el 5 de octubre de 2026" in body
        assert "Bancolombia, ahorros 123-456789-00" in body
        assert "Nequi 300 123 4567" in body
        assert "adjunta en PDF" in body


def test_first_reminder_says_the_balance_and_how_to_pay() -> None:
    email = render_email("reminder_1", EMAIL, date(2026, 10, 6))

    assert email.subject == "Recordatorio: cuenta de cobro N.º 0031 pendiente"
    for body in (email.html, email.text):
        assert "$600.000" in body
        assert "$1.000.000" not in body
        assert "Venció el 5 de octubre de 2026" in body
        assert "Nequi 300 123 4567" in body


def test_second_reminder_says_the_days_overdue() -> None:
    email = render_email("reminder_2", EMAIL, TODAY)

    assert "8 días de atraso" in email.subject
    for body in (email.html, email.text):
        assert "$600.000" in body
        assert "8 días de atraso" in body


def test_manual_reminder_before_the_due_date_does_not_say_it_is_late() -> None:
    email = render_email("manual_reminder", EMAIL, date(2026, 10, 3))

    for body in (email.html, email.text):
        assert "Vence el 5 de octubre de 2026" in body
        assert "Venció" not in body


def test_receipt_says_what_was_paid_and_what_is_left() -> None:
    partial = render_email("receipt", EMAIL, TODAY)
    full = render_email("receipt", replace(EMAIL, balance=0), TODAY)

    for body in (partial.html, partial.text):
        assert "$400.000" in body
        assert "12 de octubre de 2026 · Transferencia" in body
        assert "Saldo restante" in body and "$600.000" in body
        assert "adjunta" not in body
    for body in (full.html, full.text):
        assert "La cuenta queda pagada." in body
        assert "Saldo restante" not in body


def test_without_payment_details_the_section_is_left_out() -> None:
    email = render_email("bill", replace(EMAIL, payment_details=None), TODAY)

    assert "Datos de pago" not in email.html
    assert "Datos de pago" not in email.text


def test_what_people_typed_is_escaped_in_the_html() -> None:
    hostile = replace(
        EMAIL,
        tenant_name="<script>alert(1)</script>",
        concept='Arreglo <img src=x onerror="x">',
        payment_details="<b>Nequi</b>",
    )

    email = render_email("bill", hostile, TODAY)

    # The layout has an image of its own, the isotipo: only the one typed must not get in.
    assert "<script>" not in email.html and "<img src=x" not in email.html
    assert 'onerror="x"' not in email.html and "<b>" not in email.html
    assert "&lt;script&gt;" in email.html
    # Plain text is shown as typed.
    assert "<b>Nequi</b>" in email.text


def test_concept_starts_lowercase_mid_sentence_unless_it_starts_with_an_acronym() -> None:
    usual = render_email("bill", EMAIL, TODAY)
    acronym = render_email("bill", replace(EMAIL, concept="IVA del canon · Apto 2"), TODAY)

    assert "la cuenta de cobro de canon de arrendamiento" in usual.text
    assert "la cuenta de cobro de IVA del canon" in acronym.text
    assert "iVA" not in acronym.text and "iVA" not in acronym.html
