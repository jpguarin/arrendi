"""How the bill shows money, dates and its number. Spanish, as in Colombia."""

from datetime import date

MONTHS = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)


def format_pesos(amount: int) -> str:
    """Whole pesos, with a dot every three digits: `$1.000.000`."""
    return f"${amount:,}".replace(",", ".")


def format_long_date(day: date) -> str:
    """`5 de octubre de 2026`."""
    return f"{day.day} de {MONTHS[day.month - 1]} de {day.year}"


def format_month(day: date) -> str:
    """`Octubre 2026`."""
    return f"{MONTHS[day.month - 1].capitalize()} {day.year}"


def format_number(number: int) -> str:
    """`N.º 0031`."""
    return f"N.º {number:04d}"


def late_fee_notice(amount: int, deadline: date) -> str:
    """What a bill says about paying it late. The fee goes on the next bill, not on it."""
    return (
        f"Si se paga después del {format_long_date(deadline)}, la siguiente cuenta "
        f"incluirá un recargo por mora de {format_pesos(amount)}."
    )
