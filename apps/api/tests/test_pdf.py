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
    tenant_document_type="cc",
    tenant_document="80.111.222",
    lines=[BillLine("Canon de arrendamiento", 1_000_000, "Octubre 2026 - Apto 2")],
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
        b"C.C. 80.111.222",
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


def test_pdf_says_whether_the_tenants_document_is_a_cedula_or_a_nit() -> None:
    pdf = render_bill(replace(BILL, tenant_document_type="nit", tenant_document="901.555.111-2"))

    assert b"NIT 901.555.111-2" in pdf
    assert b"C.C./NIT" not in pdf


def test_voided_bill_is_marked() -> None:
    assert b"ANULADA" in render_bill(replace(BILL, voided=True))


def test_long_texts_do_not_break_the_page() -> None:
    long = replace(
        BILL,
        lines=[BillLine("Arreglo de la tuberia del patio " * 8, 350_000, "Apto 2")],
        payment_details="Bancolombia " * 40,
    )

    assert render_bill(long).startswith(b"%PDF-")


def pages(pdf: bytes) -> int:
    return pdf.count(b"/Type /Page\n")


def test_each_line_shows_its_own_amount_and_only_the_first_says_what_the_bill_is_about() -> None:
    pdf = render_bill(
        replace(
            BILL,
            lines=[
                *BILL.lines,
                BillLine("Administracion", 200_000),
                BillLine("Parqueadero", 80_000),
            ],
            total=1_280_000,
        )
    )

    for text in (b"$1.000.000", b"Administracion", b"$200.000", b"Parqueadero", b"$80.000"):
        assert text in pdf
    assert b"Total a pagar" in pdf and b"$1.280.000" in pdf
    assert pdf.count(b"Octubre 2026 - Apto 2") == 1
    assert pages(pdf) == 1


def test_the_fullest_monthly_bill_fits_on_one_page() -> None:
    # The rent, ten items of the lease and the deposit.
    lines = [*BILL.lines, *(BillLine(f"Concepto {n}", 10_000 * n) for n in range(1, 12))]

    assert pages(render_bill(replace(BILL, lines=lines, total=1_660_000))) == 1


def test_a_bill_too_long_for_a_page_goes_on_to_the_next_with_nothing_lost() -> None:
    lines = [BillLine(f"Concepto {n} " + "muy largo " * 18, 1_000 * n) for n in range(1, 13)]
    bill = replace(BILL, lines=lines, total=78_000, payment_details="Banco " * 80, voided=True)

    pdf = render_bill(bill)

    assert pages(pdf) > 1
    for n in range(1, 13):
        assert f"Concepto {n} ".encode() in pdf
    assert b"Total a pagar" in pdf and b"$78.000" in pdf and b"Vence el" in pdf
    # Every page says it is voided.
    assert pdf.count(b"ANULADA") == pages(pdf)
