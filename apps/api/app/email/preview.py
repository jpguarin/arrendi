"""Writes every email with sample data, to look at the templates in a browser.

    python -m app.email.preview

Nothing is sent and nothing is read from the database: the figures are made up here.
"""

import tempfile
import webbrowser
from dataclasses import replace
from datetime import date
from html import escape
from pathlib import Path

from app.email.content import KINDS, BillEmail, render_email

TODAY = date(2026, 10, 12)
SAMPLE = BillEmail(
    owner_name="Carolina Vélez Ruiz",
    tenant_name="Julián Pardo",
    number=42,
    concept="Canon de arrendamiento · Octubre 2026 · Apto 201",
    total=1_300_000,
    balance=1_300_000,
    due_date=date(2026, 10, 15),
    payment_details="Bancolombia · Ahorros 123-456789-01\nNequi 310 555 0142",
)
# What each email is about: the reminders go out after the due date, and the receipt
# follows a payment that leaves a balance.
SAMPLES = {
    "bill": SAMPLE,
    "reminder_1": replace(SAMPLE, due_date=date(2026, 10, 11)),
    "reminder_2": replace(SAMPLE, due_date=date(2026, 10, 5)),
    "manual_reminder": replace(SAMPLE, due_date=date(2026, 10, 5)),
    "receipt": replace(
        SAMPLE,
        balance=700_000,
        payment_amount=600_000,
        payment_date=date(2026, 10, 8),
        payment_method="Nequi",
    ),
}


def write_previews(folder: Path) -> Path:
    """One HTML and one text file per email, and an index that shows them all."""
    folder.mkdir(parents=True, exist_ok=True)
    sections = []
    for kind in KINDS:
        email = render_email(kind, SAMPLES[kind], TODAY)
        (folder / f"{kind}.html").write_text(email.html, encoding="utf-8")
        (folder / f"{kind}.txt").write_text(email.text, encoding="utf-8")
        sections.append(
            f"<h2>{kind}</h2><p>Asunto: {escape(email.subject)}</p>"
            f'<div class="pair"><iframe src="{kind}.html" title="{kind}"></iframe>'
            f"<pre>{escape(email.text)}</pre></div>"
        )
    index = folder / "index.html"
    index.write_text(
        '<!doctype html><html lang="es"><meta charset="utf-8"><title>Correos de Arrendi</title>'
        "<style>body{font-family:system-ui,sans-serif;margin:24px;color:#14264C}"
        "h2{margin:32px 0 4px}p{margin:0 0 12px;color:#55607A}"
        ".pair{display:flex;gap:16px;flex-wrap:wrap;align-items:flex-start}"
        "iframe{width:560px;max-width:100%;height:640px;border:1px solid #DFE3EC;border-radius:8px}"
        "pre{flex:1;min-width:280px;margin:0;padding:16px;background:#F5F6F9;border-radius:8px;"
        "white-space:pre-wrap;font-size:13px}</style>"
        "<h1>Correos de Arrendi</h1><p>Datos de ejemplo. A la izquierda el HTML; "
        "a la derecha, el texto plano.</p>" + "".join(sections) + "</html>",
        encoding="utf-8",
    )
    return index


if __name__ == "__main__":
    page = write_previews(Path(tempfile.gettempdir()) / "arrendi-emails")
    print(page)
    webbrowser.open(page.as_uri())
