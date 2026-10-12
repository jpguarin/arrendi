"""Writes sample bills as PDF, to look at the document without issuing one.

    python -m app.pdf.preview

Nothing is read from the database or storage: the figures are made up here.
"""

import tempfile
import webbrowser
from dataclasses import replace
from datetime import date
from pathlib import Path

from app.pdf.bill import BillDocument, BillLine, render_bill

SAMPLE = BillDocument(
    number=43,
    issue_date=date(2026, 10, 1),
    due_date=date(2026, 10, 5),
    owner_name="Carolina Vélez Ruiz",
    owner_document_type="cc",
    owner_document="52.418.907",
    tenant_name="Panadería El Trigal SAS",
    tenant_document_type="nit",
    tenant_document="901.234.567-8",
    lines=[
        BillLine("Canon de arrendamiento", "Octubre 2026 · Local 1", 1_950_000),
        BillLine("Administración", "Octubre 2026 · Local 1", 150_000),
    ],
    total=2_100_000,
    payment_details="Bancolombia · Ahorros 123-456789-01\nNequi 310 555 0142",
)
# The cases the document has to hold: a usual bill, one with nothing optional filled
# in, and a voided one.
SAMPLES = {
    "cuenta": SAMPLE,
    "cuenta-minima": replace(
        SAMPLE, owner_document=None, tenant_document=None, payment_details=None
    ),
    "cuenta-anulada": replace(SAMPLE, voided=True),
}


def write_previews(folder: Path) -> list[Path]:
    folder.mkdir(parents=True, exist_ok=True)
    files = []
    for name, bill in SAMPLES.items():
        file = folder / f"{name}.pdf"
        file.write_bytes(render_bill(bill))
        files.append(file)
    return files


if __name__ == "__main__":
    for preview in write_previews(Path(tempfile.gettempdir()) / "arrendi-pdf"):
        print(preview)
        webbrowser.open(preview.as_uri())
