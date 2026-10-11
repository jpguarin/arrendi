from dataclasses import replace
from datetime import date

from app.pdf.bill import BillDocument, BillLine, render_bill
from app.pdf.format import format_long_date, format_month, format_number, format_pesos

BILL = BillDocument(
    number=31,
    issue_date=date(2026, 10, 1),
    due_date=date(2026, 10, 5),
    owner_name="Ana Gomez",
    owner_document_type="cc",
    owner_document="52.123.456",
    tenant_name="Carlos Rojas",
    tenant_document="80.111.222",
    lines=[BillLine("Canon de arrendamiento", "Octubre 2026 - Apto 2", 1_000_000)],
    total=1_000_000,
    payment_details="Bancolombia, ahorros 123-456789-00\nNequi 300 123 4567",
)


def test_money_has_a_dot_every_three_digits() -> None:
    assert format_pesos(950) == "$950"
    assert format_pesos(950000) == "$950.000"
    assert format_pesos(1_000_000) == "$1.000.000"


def test_dates_are_written_in_spanish() -> None:
    assert format_long_date(date(2026, 10, 5)) == "5 de octubre de 2026"
    assert format_long_date(date(2027, 1, 28)) == "28 de enero de 2027"
    assert format_month(date(2026, 10, 1)) == "Octubre 2026"


def test_number_is_padded_to_four_digits() -> None:
    assert format_number(31) == "N.º 0031"
    assert format_number(12345) == "N.º 12345"


def test_pdf_shows_everything_the_tenant_needs() -> None:
    pdf = render_bill(BILL)

    assert pdf.startswith(b"%PDF-")
    for text in (
        b"Cuenta de cobro",
        b"0031",
        b"1 de octubre de 2026",
        b"Ana Gomez",
        b"C.C. 52.123.456",
        b"C.C./NIT 80.111.222",
        b"Carlos Rojas",
        b"80.111.222",
        b"Canon de arrendamiento",
        b"Octubre 2026 - Apto 2",
        b"$1.000.000",
        b"Total a pagar",
        b"Vence el 5 de octubre de 2026",
        b"Pagar a: Bancolombia, ahorros 123-456789-00",
        b"Nequi 300 123 4567",
        b"Arrendi",
    ):
        assert text in pdf, text
    assert b"ANULADA" not in pdf


def test_pdf_leaves_out_what_the_owner_has_not_filled_in() -> None:
    pdf = render_bill(
        replace(BILL, owner_document=None, tenant_document=None, payment_details=None)
    )

    assert b"C.C." not in pdf
    assert b"Pagar a" not in pdf
    assert b"Vence el" in pdf


def test_pdf_says_whether_the_owners_document_is_a_cedula_or_a_nit() -> None:
    pdf = render_bill(replace(BILL, owner_document_type="nit", owner_document="900.123.456-7"))

    assert b"NIT 900.123.456-7" in pdf
    assert b"C.C. 900" not in pdf


def test_voided_bill_is_marked() -> None:
    assert b"ANULADA" in render_bill(replace(BILL, voided=True))


def test_long_texts_do_not_break_the_page() -> None:
    long = replace(
        BILL,
        lines=[BillLine("Arreglo de la tuberia del patio " * 8, "Apto 2", 350_000)],
        payment_details="Bancolombia " * 40,
    )

    assert render_bill(long).startswith(b"%PDF-")
