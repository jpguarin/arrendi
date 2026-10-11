"""The bill as a PDF. One template, always in the light theme.

Nothing here reads the database or storage: it turns what it is given into bytes.
"""

from dataclasses import dataclass
from datetime import date
from io import BytesIO

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen.canvas import Canvas

from app.pdf.format import format_long_date, format_number, format_pesos

# The light palette of docs/diseno.md.
FOREGROUND = HexColor("#14201C")
MUTED = HexColor("#55635E")
SOFT = HexColor("#3A4743")
BORDER = HexColor("#E1E6E3")
BACKGROUND = HexColor("#F3F5F4")
ALERT = HexColor("#8A3D06")

# Helvetica comes with every PDF reader, so no font file travels with the API.
REGULAR = "Helvetica"
BOLD = "Helvetica-Bold"

WIDTH, HEIGHT = letter
MARGIN = 64
RIGHT = WIDTH - MARGIN
CONTENT = WIDTH - 2 * MARGIN


@dataclass(frozen=True)
class BillLine:
    description: str
    # What the description is about, like "Octubre 2026 · Apto 2".
    detail: str
    amount: int


@dataclass(frozen=True)
class BillDocument:
    number: int
    issue_date: date
    due_date: date
    owner_name: str
    # "cc" or "nit": what the owner's document is.
    owner_document_type: str
    owner_document: str | None
    tenant_name: str
    tenant_document: str | None
    lines: list[BillLine]
    total: int
    payment_details: str | None
    voided: bool = False


OWNER_DOCUMENT_LABELS = {"cc": "C.C.", "nit": "NIT"}


def _with_document(name: str, document: str | None) -> str:
    # The tenant's document has no type yet: it may be either.
    return f"{name} · C.C./NIT {document}" if document else name


def _rule(canvas: Canvas, y: float) -> None:
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(1)
    canvas.line(MARGIN, y, RIGHT, y)


def _wrapped(text: str, font: str, size: float, width: float) -> list[str]:
    """The text cut into lines that fit, keeping the line breaks it already has."""
    lines: list[str] = []
    for paragraph in text.splitlines():
        lines.extend(simpleSplit(paragraph, font, size, width) or [""])
    return lines


def render_bill(bill: BillDocument) -> bytes:
    buffer = BytesIO()
    # Not compressed: the file is one small page, and its text can be found in it.
    canvas = Canvas(buffer, pagesize=letter, pageCompression=0)
    canvas.setTitle(f"Cuenta de cobro {format_number(bill.number)}")
    canvas.setAuthor(bill.owner_name)

    # Heading: what it is on the left, who issues it on the right.
    y = HEIGHT - MARGIN - 8
    canvas.setFillColor(FOREGROUND)
    canvas.setFont(BOLD, 20)
    canvas.drawString(MARGIN, y, "Cuenta de cobro")
    canvas.setFont(BOLD, 11)
    canvas.drawRightString(RIGHT, y + 4, bill.owner_name)
    canvas.setFillColor(MUTED)
    canvas.setFont(REGULAR, 11)
    if bill.owner_document:
        label = OWNER_DOCUMENT_LABELS[bill.owner_document_type]
        canvas.drawRightString(RIGHT, y - 12, f"{label} {bill.owner_document}")
    y -= 20
    canvas.drawString(
        MARGIN, y, f"{format_number(bill.number)} · {format_long_date(bill.issue_date)}"
    )

    y -= 22
    _rule(canvas, y)

    # Who owes.
    y -= 26
    canvas.setFont(REGULAR, 10)
    canvas.drawString(MARGIN, y, "Debe")
    y -= 17
    canvas.setFillColor(FOREGROUND)
    canvas.setFont(BOLD, 12)
    canvas.drawString(MARGIN, y, _with_document(bill.tenant_name, bill.tenant_document))

    # What for.
    y -= 34
    for line in bill.lines:
        canvas.setFillColor(FOREGROUND)
        canvas.setFont(BOLD, 12)
        canvas.drawRightString(RIGHT, y, format_pesos(line.amount))
        canvas.setFont(REGULAR, 12)
        for text in _wrapped(line.description, REGULAR, 12, CONTENT - 120):
            canvas.drawString(MARGIN, y, text)
            y -= 16
        canvas.setFillColor(MUTED)
        canvas.setFont(REGULAR, 11)
        canvas.drawString(MARGIN, y, line.detail)
        y -= 24

    _rule(canvas, y)

    y -= 34
    canvas.setFillColor(FOREGROUND)
    canvas.setFont(BOLD, 12)
    canvas.drawString(MARGIN, y, "Total a pagar")
    canvas.setFont(BOLD, 22)
    canvas.drawRightString(RIGHT, y - 2, format_pesos(bill.total))

    # When and how to pay.
    notes = [f"Vence el {format_long_date(bill.due_date)}"]
    if bill.payment_details:
        notes.extend(_wrapped(f"Pagar a: {bill.payment_details}", REGULAR, 11, CONTENT - 28))
    box_height = 24 + 16 * len(notes)
    y -= 26 + box_height
    canvas.setFillColor(BACKGROUND)
    canvas.roundRect(MARGIN, y, CONTENT, box_height, 6, stroke=0, fill=1)
    canvas.setFillColor(SOFT)
    canvas.setFont(REGULAR, 11)
    text_y = y + box_height - 24
    for note in notes:
        canvas.drawString(MARGIN + 14, text_y, note)
        text_y -= 16

    canvas.setFillColor(MUTED)
    canvas.setFont(REGULAR, 9)
    canvas.drawCentredString(WIDTH / 2, MARGIN / 2, "Arrendi")

    if bill.voided:
        # Across the page, so no copy of it passes for a bill still owed.
        canvas.saveState()
        canvas.translate(WIDTH / 2, HEIGHT / 2)
        canvas.rotate(35)
        canvas.setFillColor(ALERT, alpha=0.3)
        canvas.setFont(BOLD, 96)
        canvas.drawCentredString(0, 0, "ANULADA")
        canvas.restoreState()

    canvas.showPage()
    canvas.save()
    return buffer.getvalue()
