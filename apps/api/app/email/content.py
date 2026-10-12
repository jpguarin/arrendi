"""What each email says. Templates in Jinja2, in HTML and in plain text."""

from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from app.pdf.format import format_long_date, format_number, format_pesos

# The receipt has no notification of its own kind of bill: it is about a payment.
KINDS = ("bill", "reminder_1", "reminder_2", "manual_reminder", "receipt")

# The isotipo at the foot of every email travels inside it, and the HTML points to it
# by this id. Mail readers do not draw SVG, so it is a PNG of
# docs/new-brand-design/isotype.svg.
BRAND_MARK_CID = "arrendi-isotype"
BRAND_MARK = (Path(__file__).parent / "assets" / "isotype.png").read_bytes()

_environment = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    # What the owner and the tenant typed is text, never markup. Plain text stays as is.
    autoescape=select_autoescape(["html"]),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)
_environment.filters["pesos"] = format_pesos
_environment.filters["long_date"] = format_long_date


@dataclass(frozen=True)
class BillEmail:
    """What the emails about a bill need to know."""

    owner_name: str
    tenant_name: str
    number: int
    # What is charged, like "Canon de arrendamiento · Octubre 2026 · Apto 2".
    concept: str
    total: int
    balance: int
    due_date: date
    payment_details: str | None
    # Only for the receipt.
    payment_amount: int | None = None
    payment_date: date | None = None
    payment_method: str | None = None


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    html: str
    text: str


def _subject(kind: str, number: str, days_overdue: int) -> str:
    return {
        "bill": f"Cuenta de cobro {number}",
        "reminder_1": f"Recordatorio: cuenta de cobro {number} pendiente",
        "reminder_2": (
            f"Segundo recordatorio: cuenta de cobro {number}, {days_overdue} días de atraso"
        ),
        "manual_reminder": f"Recordatorio de pago: cuenta de cobro {number}",
        "receipt": f"Recibo de pago: cuenta de cobro {number}",
    }[kind]


def render_email(kind: str, email: BillEmail, today: date) -> RenderedEmail:
    days_overdue = max((today - email.due_date).days, 0)
    number = format_number(email.number)
    subject = _subject(kind, number, days_overdue)
    due = format_long_date(email.due_date)
    context = asdict(email) | {
        "subject": subject,
        "brand_mark_cid": BRAND_MARK_CID,
        "number": number,
        # Mid-sentence: "la cuenta de cobro de canon de arrendamiento · …".
        "concept_lower": email.concept[:1].lower() + email.concept[1:],
        "days_overdue": days_overdue,
        "due_line": f"Venció el {due}" if days_overdue else f"Vence el {due}",
    }
    return RenderedEmail(
        subject=subject,
        html=_environment.get_template(f"{kind}.html").render(context),
        text=_environment.get_template(f"{kind}.txt").render(context).strip() + "\n",
    )
