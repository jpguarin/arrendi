// How Arrendi shows money and dates (CLAUDE.md): `$1.000.000` and `5 oct 2026`.
// Written by hand instead of with Intl, whose output for es-CO changes between
// browsers and versions (a space after the sign, "5 de oct de 2026").

const MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

/** Whole pesos, with a dot every three digits: `$1.000.000`. */
export function formatPesos(amount: number): string {
  const digits = Math.abs(Math.trunc(amount))
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `${amount < 0 ? "-" : ""}$${digits}`;
}

/** What the owner typed in a money field, as whole pesos. Null when there are no digits. */
export function parsePesos(text: string): number | null {
  const digits = text.replace(/\D/g, "");
  return digits ? Number(digits) : null;
}

/**
 * A business date (`2026-10-05`) as `5 oct 2026`.
 *
 * The date is read as written, without a time zone: building a `Date` from it would
 * move it to the day before for anyone west of Greenwich, like Colombia.
 */
export function formatDate(isoDate: string): string {
  const [year, month, day] = isoDate.slice(0, 10).split("-").map(Number);
  return `${day} ${MONTHS[month - 1]} ${year}`;
}

/** The instant something happened (`2026-10-05T03:00:00Z`), as a date in Colombia. */
export function formatDateTime(isoInstant: string): string {
  const day = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Bogota" }).format(
    new Date(isoInstant),
  );
  return formatDate(day);
}

/** Today's business date (`2026-10-05`). "Today" is always the day in Colombia. */
export function todayInBogota(now: Date = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Bogota" }).format(now);
}
