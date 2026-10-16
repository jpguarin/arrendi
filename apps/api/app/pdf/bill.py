"""The bill as a PDF. One template, always in the light theme.

Nothing here reads the database or storage: it turns what it is given into bytes.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from io import BytesIO

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfgen.canvas import FILL_NON_ZERO, Canvas

from app.pdf.format import (
    format_long_date,
    format_number,
    format_pesos,
    format_short_date,
    late_fee_notice,
)
from app.pdf.logo import GREEN_PATHS, INK_PATHS, SIZE

# The light palette of docs/diseno.md, on the brand of docs/new-brand-design.
FOREGROUND = HexColor("#14264C")
MUTED = HexColor("#55607A")
SOFT = HexColor("#33456E")
BORDER = HexColor("#DFE3EC")
BACKGROUND = HexColor("#F5F6F9")
ALERT = HexColor("#A3321E")
BRAND_GREEN = HexColor("#28B779")

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
    amount: int
    # What it is for, like "Octubre 2026 · Apto 2": the rent of a monthly bill says it.
    detail: str | None = None


@dataclass(frozen=True)
class BillDocument:
    number: int
    issue_date: date
    due_date: date
    owner_name: str
    # "cc" or "nit": what each document is.
    owner_document_type: str
    owner_document: str | None
    tenant_name: str
    tenant_document_type: str
    tenant_document: str | None
    lines: list[BillLine]
    total: int
    payment_details: str | None
    voided: bool = False
    # The unit, for the heading of a manual bill: none of its lines says where it is from.
    unit_name: str | None = None
    # What paying late costs and the last day to pay in time. Both or neither.
    late_fee_amount: int | None = None
    late_fee_deadline: date | None = None
    # The image the owner signs with, as a PNG or a JPG. Without it the bill leaves a
    # line to sign by hand.
    signature: bytes | None = None


DOCUMENT_LABELS = {"cc": "C.C.", "nit": "NIT"}


# Room for "Cobra" and "Debe", to the left of the names.
PARTY_LABEL = 52


def _rule(canvas: Canvas, y: float) -> None:
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(1)
    canvas.line(MARGIN, y, RIGHT, y)


_COMMAND = re.compile(r"([MLHVCZ])([^MLHVCZ]*)")


def _trace(canvas: Canvas, data: str):
    """An SVG path made only of absolute M, L, H, V, C and Z, as a path of the canvas."""
    path = canvas.beginPath()
    x = y = 0.0
    for command, arguments in _COMMAND.findall(data):
        numbers = [float(number) for number in arguments.replace(",", " ").split()]
        if command == "M":
            x, y = numbers
            path.moveTo(x, y)
        elif command == "L":
            x, y = numbers
            path.lineTo(x, y)
        elif command == "H":
            (x,) = numbers
            path.lineTo(x, y)
        elif command == "V":
            (y,) = numbers
            path.lineTo(x, y)
        elif command == "C":
            path.curveTo(*numbers)
            x, y = numbers[4:]
        else:
            path.close()
    return path


def _brand_mark(canvas: Canvas, x: float, y: float, height: float) -> None:
    """The isotipo of the brand, with its bottom left corner at `x`, `y`."""
    scale = height / SIZE[1]
    canvas.saveState()
    # The isotipo measures from its top left corner, with `y` growing downwards.
    canvas.translate(x, y + height)
    canvas.scale(scale, -scale)
    for color, paths in ((FOREGROUND, INK_PATHS), (BRAND_GREEN, GREEN_PATHS)):
        canvas.setFillColor(color)
        for data in paths:
            canvas.drawPath(_trace(canvas, data), stroke=0, fill=1, fillMode=FILL_NON_ZERO)
    canvas.restoreState()


def _wrapped(text: str, font: str, size: float, width: float) -> list[str]:
    """The text cut into lines that fit, keeping the line breaks it already has."""
    lines: list[str] = []
    for paragraph in text.splitlines():
        lines.extend(simpleSplit(paragraph, font, size, width) or [""])
    return lines


# The foot of every page, from the bottom edge up: the brand mark, the bill and the page,
# and a rule over them. Below `BOTTOM` the page belongs to it.
FOOT_MARK = 16
FOOT_TEXT = 44
FOOT_RULE = 60
BOTTOM = FOOT_RULE + 24


class _PagedCanvas(Canvas):
    """Holds every page until the bill ends, so that each foot can say how many there are."""

    def __init__(self, *args, foot: Callable[[Canvas, int], None], **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._foot = foot
        self._pages: list[dict] = []

    def showPage(self) -> None:
        self._pages.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        for page in self._pages:
            self.__dict__.update(page)
            self._foot(self, len(self._pages))
            super().showPage()
        super().save()


def _foot(canvas: Canvas, bill: BillDocument, pages: int) -> None:
    """Which bill and which page, under a rule; and the brand, small: the bill is the
    owner's, Arrendi only issues it."""
    _rule(canvas, FOOT_RULE)
    canvas.setFillColor(MUTED)
    canvas.setFont(REGULAR, 9)
    canvas.drawString(
        MARGIN, FOOT_TEXT, f"{format_number(bill.number)} · {format_short_date(bill.issue_date)}"
    )
    canvas.drawRightString(RIGHT, FOOT_TEXT, f"Página {canvas.getPageNumber()} de {pages}")
    mark_height = 14
    mark_width = SIZE[0] * mark_height / SIZE[1]
    _brand_mark(canvas, (WIDTH - mark_width) / 2, FOOT_MARK, mark_height)


def _open_page(canvas: Canvas) -> float:
    """Draws what every page starts with and returns where its content begins."""
    # A band of the brand color across the top edge.
    canvas.setFillColor(FOREGROUND)
    canvas.rect(0, HEIGHT - 8, WIDTH, 8, stroke=0, fill=1)
    return HEIGHT - MARGIN - 8


def _next_page(canvas: Canvas, bill: BillDocument) -> float:
    """Closes the page and opens another, which says on its own which bill it is part of.

    Its number is in the foot."""
    _close_page(canvas, bill)
    y = _open_page(canvas)
    canvas.setFillColor(MUTED)
    canvas.setFont(REGULAR, 10)
    whose = f"Cuenta de cobro {format_number(bill.number)} · {bill.owner_name}"
    canvas.drawString(MARGIN, y, _wrapped(whose, REGULAR, 10, CONTENT)[0])
    y -= 14
    _rule(canvas, y)
    return y - 28


def _close_page(canvas: Canvas, bill: BillDocument) -> None:
    # The foot is drawn when the bill ends, once the number of pages is known.
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


class SignatureError(Exception):
    """The bill has a signature and it could not be drawn."""


# The signature: no larger than this, and the line to sign on when there is none.
SIGNATURE_WIDTH = 180
SIGNATURE_HEIGHT = 60


def _signature(canvas: Canvas, bill: BillDocument, y: float) -> None:
    """Closes the bill at the foot of the page: the signature, the name and the document.

    `y` is where the content above ends. If it reaches the foot, the block gets a page
    of its own.
    """
    name = _wrapped(bill.owner_name, BOLD, 11, CONTENT)
    document = (
        f"{DOCUMENT_LABELS[bill.owner_document_type]} {bill.owner_document}"
        if bill.owner_document
        else None
    )
    # From the foot up: the document, the name, and the signature over them.
    text_height = 14 * len(name) + (14 if document else 0)
    signature_y = BOTTOM + text_height + 8
    if y - 24 < signature_y + SIGNATURE_HEIGHT:
        _next_page(canvas, bill)

    if bill.signature:
        try:
            image = ImageReader(BytesIO(bill.signature))
            width, height = image.getSize()
            # As large as fits, and never more than a point per pixel.
            scale = min(SIGNATURE_WIDTH / width, SIGNATURE_HEIGHT / height, 1)
            canvas.drawImage(image, MARGIN, signature_y, width * scale, height * scale, mask="auto")
        except Exception as error:
            # Not drawn as if it had none: a bill that is kept as signed has to be signed.
            raise SignatureError from error
    else:
        canvas.setStrokeColor(MUTED)
        canvas.setLineWidth(0.75)
        canvas.line(MARGIN, signature_y, MARGIN + SIGNATURE_WIDTH, signature_y)

    text_y = signature_y - 16
    canvas.setFillColor(FOREGROUND)
    canvas.setFont(BOLD, 11)
    for text in name:
        canvas.drawString(MARGIN, text_y, text)
        text_y -= 14
    if document:
        canvas.setFillColor(MUTED)
        canvas.setFont(REGULAR, 11)
        canvas.drawString(MARGIN, text_y, document)


def _room(canvas: Canvas, bill: BillDocument, y: float, height: float) -> float:
    """Where to draw something `height` tall: here, or on a new page if it does not fit."""
    if y - height >= BOTTOM:
        return y
    return _next_page(canvas, bill)


def render_bill(bill: BillDocument) -> bytes:
    buffer = BytesIO()
    # Not compressed: the file is small, and its text can be found in it.
    canvas = _PagedCanvas(
        buffer,
        pagesize=letter,
        pageCompression=0,
        foot=lambda page, pages: _foot(page, bill, pages),
    )
    canvas.setTitle(f"Cuenta de cobro {format_number(bill.number)}")
    canvas.setAuthor(bill.owner_name)
    # The name of the brand is drawn, not written: this keeps it in the file as text.
    canvas.setCreator("Arrendi")

    # Heading: what it is on the left, who issues it on the right.
    y = _open_page(canvas)
    canvas.setFillColor(FOREGROUND)
    canvas.setFont(BOLD, 20)
    canvas.drawString(MARGIN, y, "Cuenta de cobro")
    canvas.drawRightString(RIGHT, y, format_number(bill.number))
    # Below the title: when it was issued and, in a manual bill, the unit it is for.
    issued = format_long_date(bill.issue_date)
    if bill.unit_name:
        issued = f"{issued} · {bill.unit_name}"
    canvas.setFillColor(MUTED)
    canvas.setFont(REGULAR, 11)
    y -= 5
    for text in _wrapped(issued, REGULAR, 11, CONTENT):
        y -= 15
        canvas.drawString(MARGIN, y, text)

    y -= 22
    _rule(canvas, y)

    # Who charges and who owes: a label, then the name across the page, on as many lines
    # as it needs, and the document under it.
    y -= 28
    for label, name, document_type, document in (
        ("Cobra", bill.owner_name, bill.owner_document_type, bill.owner_document),
        ("Debe", bill.tenant_name, bill.tenant_document_type, bill.tenant_document),
    ):
        canvas.setFillColor(MUTED)
        canvas.setFont(REGULAR, 10)
        canvas.drawString(MARGIN, y, label)
        canvas.setFillColor(FOREGROUND)
        canvas.setFont(BOLD, 12)
        for text in _wrapped(name, BOLD, 12, CONTENT - PARTY_LABEL):
            canvas.drawString(MARGIN + PARTY_LABEL, y, text)
            y -= 16
        if document:
            canvas.setFillColor(MUTED)
            canvas.setFont(REGULAR, 11)
            canvas.drawString(
                MARGIN + PARTY_LABEL, y, f"{DOCUMENT_LABELS[document_type]} {document}"
            )
            y -= 16
        y -= 8
    y += 4
    _rule(canvas, y)

    # What for: each thing charged, with its own amount.
    y -= 30
    for line in bill.lines:
        description = _wrapped(line.description, REGULAR, 12, CONTENT - 120)
        # A line is never split between two pages.
        y = _room(canvas, bill, y, 16 * len(description) + (11 if line.detail else 0))
        canvas.setFillColor(FOREGROUND)
        canvas.setFont(BOLD, 12)
        canvas.drawRightString(RIGHT, y, format_pesos(line.amount))
        canvas.setFont(REGULAR, 12)
        for text in description:
            canvas.drawString(MARGIN, y, text)
            y -= 16
        if line.detail:
            canvas.setFillColor(MUTED)
            canvas.setFont(REGULAR, 11)
            canvas.drawString(MARGIN, y, line.detail)
            y -= 16
        y -= 8

    # The total: the sum of the lines above. It stays with the rule that closes them.
    y = _room(canvas, bill, y, 34 + 4)
    _rule(canvas, y)

    y -= 34
    canvas.setFillColor(FOREGROUND)
    canvas.setFont(BOLD, 12)
    canvas.drawString(MARGIN, y, "Total a pagar")
    canvas.setFont(BOLD, 22)
    canvas.drawRightString(RIGHT, y - 2, format_pesos(bill.total))

    # When and how to pay.
    notes = [f"Vence el {format_long_date(bill.due_date)}"]
    if bill.late_fee_amount and bill.late_fee_deadline:
        notice = late_fee_notice(bill.late_fee_amount, bill.late_fee_deadline)
        notes.extend(_wrapped(notice, REGULAR, 11, CONTENT - 28))
    if bill.payment_details:
        notes.extend(_wrapped(f"Pagar a: {bill.payment_details}", REGULAR, 11, CONTENT - 28))
    # In a box, or in one on each page when they are more than the page has room for.
    while notes:
        fit = int((y - 26 - 24 - BOTTOM) // 16)
        if fit < min(len(notes), 2):
            # Not even a couple of lines: better to start the box on a fresh page.
            y = _next_page(canvas, bill)
            continue
        here, notes = notes[:fit], notes[fit:]
        box_height = 24 + 16 * len(here)
        y -= 26 + box_height
        canvas.setFillColor(BACKGROUND)
        canvas.roundRect(MARGIN, y, CONTENT, box_height, 6, stroke=0, fill=1)
        canvas.setFillColor(SOFT)
        canvas.setFont(REGULAR, 11)
        text_y = y + box_height - 24
        for note in here:
            canvas.drawString(MARGIN + 14, text_y, note)
            text_y -= 16
        if notes:
            y = _next_page(canvas, bill) + 26

    _signature(canvas, bill, y)
    _close_page(canvas, bill)
    canvas.save()
    return buffer.getvalue()
