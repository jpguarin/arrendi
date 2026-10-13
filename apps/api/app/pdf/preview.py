"""Writes sample bills as PDF, to look at the document without issuing one.

    python -m app.pdf.preview

Nothing is read from the database or storage: the figures are made up here.
"""

import tempfile
import webbrowser
from dataclasses import replace
from datetime import date
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

from app.pdf.bill import BillDocument, BillLine, render_bill


def _signature() -> bytes:
    """A few strokes that stand in for a signature, as the API stores one."""
    image = Image.new("RGBA", (600, 200), (0, 0, 0, 0))
    strokes = [(20, 150), (90, 40), (130, 160), (200, 60), (260, 150), (330, 90), (580, 110)]
    ImageDraw.Draw(image).line(strokes, fill=(20, 38, 76, 255), width=6, joint="curve")
    out = BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


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
        BillLine("Canon de arrendamiento", 1_950_000, "Octubre 2026 · Local 1"),
        BillLine("Administración", 150_000),
    ],
    total=2_100_000,
    payment_details="Bancolombia · Ahorros 123-456789-01\nNequi 310 555 0142",
    signature=_signature(),
)
# The most a monthly bill can carry: the rent, ten items of the lease and the deposit,
# with payment details as long as they get.
FULL = replace(
    SAMPLE,
    lines=[
        SAMPLE.lines[0],
        *(BillLine(f"Concepto fijo número {n} del contrato", 10_000 * n) for n in range(1, 11)),
        BillLine("Depósito", 1_950_000),
    ],
    total=4_450_000,
    payment_details="\n".join(
        f"Banco de ejemplo número {n} · Cuenta de ahorros 123-456789-0{n} a nombre de Carolina"
        for n in range(1, 7)
    ),
)
# The cases the document has to hold: a usual bill, one with nothing optional filled
# in, a voided one, one as full as it gets and one that needs a second page.
SAMPLES = {
    "cuenta": SAMPLE,
    "cuenta-minima": replace(
        SAMPLE, owner_document=None, tenant_document=None, payment_details=None
    ),
    "cuenta-anulada": replace(SAMPLE, voided=True),
    # The lease has a late fee: the bill says what paying late costs, and the next one
    # charges the fee of a month that was paid late.
    "cuenta-con-aviso-de-recargo": replace(
        SAMPLE, late_fee_amount=97_500, late_fee_deadline=date(2026, 10, 8)
    ),
    "cuenta-con-recargo": replace(
        SAMPLE,
        lines=[*SAMPLE.lines, BillLine("Recargo por mora de septiembre 2026", 97_500)],
        total=2_197_500,
        late_fee_amount=97_500,
        late_fee_deadline=date(2026, 10, 8),
    ),
    # The owner has not uploaded a signature: a line is left to sign by hand.
    "cuenta-sin-firma": replace(SAMPLE, signature=None),
    "cuenta-llena": FULL,
    # A manual bill: the unit goes in the heading, and no line says what month it is for.
    "cuenta-manual": replace(
        SAMPLE,
        lines=[BillLine("Arreglo de la chapa", 80_000), BillLine("Pintura", 45_000)],
        total=125_000,
        unit_name="Local 1",
    ),
    "cuenta-de-dos-paginas": replace(
        FULL,
        voided=True,
        lines=[
            replace(line, description=f"{line.description}, con una descripción tan larga " * 3)
            for line in FULL.lines
        ],
    ),
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
