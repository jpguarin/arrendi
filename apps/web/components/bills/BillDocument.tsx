import { BrandMark } from "@/components/Brand";
import { formatBillNumber, formatDate, formatLongDate, formatPesos } from "@/lib/format";
import { DOCUMENT_TYPE_LABELS, type DocumentType } from "@/lib/labels";
import { cn } from "@/lib/utils";

type Party = { name: string; document_type: DocumentType; document_number: string | null };

export type BillDocumentProps = {
  number: number;
  issueDate: string;
  /** Next to the date, for a bill without a line to say it under (the unit of a manual one). */
  headingNote?: string | null;
  issuer: Party & { payment_details: string | null };
  tenant: Party;
  items: { description: string; amount: number }[];
  /** Under the first line: the month and the unit of the rent. */
  ofTheRent?: string | null;
  total: number;
  dueDate: string;
  lateFeeNotice?: string | null;
  signed: boolean;
  /** The signature itself, when it is at hand; without it, a signed bill only says so. */
  signatureUrl?: string;
  /**
   * On a sheet of paper, like the PDF itself: the same in both themes, with its band on
   * top and its footer. Without it, the bill takes the colors of the screen.
   */
  paper?: boolean;
  className?: string;
};

// The colors of each look: the screen's, which follow the theme, or the paper's.
const LOOKS = {
  screen: {
    sheet: "rounded-md border border-border bg-card p-5",
    muted: "text-muted-foreground",
    rule: "border-border",
    box: "bg-background text-foreground-soft",
    signHere: "border-border-dashed",
  },
  paper: {
    sheet: "rounded-md border-t-8 border-t-ink bg-paper px-6 pt-6 pb-4 text-ink shadow-lg",
    muted: "text-ink-soft",
    rule: "border-paper-line",
    box: "bg-ink/5 text-ink-soft",
    signHere: "border-ink-soft",
  },
};
type Look = (typeof LOOKS)[keyof typeof LOOKS];

/** Who charges or who owes: the name on as many lines as it needs, its document under it. */
function PartyRow({ label, party, look }: { label: string; party: Party; look: Look }) {
  return (
    <>
      <dt className={cn("pt-0.5 text-badge font-normal", look.muted)}>{label}</dt>
      <dd className="flex min-w-0 flex-col gap-0.5">
        <span className="text-section font-semibold break-words">{party.name}</span>
        {party.document_number && (
          <span className={cn("text-support", look.muted)}>
            {DOCUMENT_TYPE_LABELS[party.document_type]} {party.document_number}
          </span>
        )}
      </dd>
    </>
  );
}

/**
 * A bill as the tenant reads it, laid out like the PDF the API makes. The stored PDF is
 * the one that counts; this is how the app shows it.
 */
export function BillDocument({
  number,
  issueDate,
  headingNote,
  issuer,
  tenant,
  items,
  ofTheRent,
  total,
  dueDate,
  lateFeeNotice,
  signed,
  signatureUrl,
  paper = false,
  className,
}: BillDocumentProps) {
  const look = paper ? LOOKS.paper : LOOKS.screen;
  return (
    <section
      aria-label="Vista previa del documento"
      className={cn("flex flex-col gap-3.5", look.sheet, className)}
    >
      <div className="flex flex-col gap-0.5">
        <div className="flex items-baseline justify-between gap-3">
          <p className="text-body font-bold">Cuenta de cobro</p>
          <p className="shrink-0 text-body font-bold">{formatBillNumber(number)}</p>
        </div>
        <p className={cn("text-badge font-normal break-words", look.muted)}>
          {formatLongDate(issueDate)}
          {headingNote && ` · ${headingNote}`}
        </p>
      </div>
      <hr className={look.rule} />
      <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-2.5">
        <PartyRow label="Cobra" party={issuer} look={look} />
        <PartyRow label="Debe" party={tenant} look={look} />
      </dl>
      <hr className={look.rule} />
      {items.map((item, index) => (
        <div key={index} className="flex justify-between gap-3 text-section">
          <p className="min-w-0 break-words">
            {item.description}
            {index === 0 && ofTheRent && (
              <>
                <br />
                <span className={cn("text-support", look.muted)}>{ofTheRent}</span>
              </>
            )}
          </p>
          <p className="shrink-0 font-semibold">{formatPesos(item.amount)}</p>
        </div>
      ))}
      <hr className={look.rule} />
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-section font-semibold">Total a pagar</p>
        <p className="text-title font-bold">{formatPesos(total)}</p>
      </div>
      <p className={cn("rounded-md px-3 py-2.5 text-support whitespace-pre-line", look.box)}>
        Vence el {formatLongDate(dueDate)}
        {lateFeeNotice && `\n${lateFeeNotice}`}
        {issuer.payment_details && `\nPagar a: ${issuer.payment_details}`}
      </p>
      {/* How the PDF ends: the signature, or a line to sign on, then who signs. */}
      <div className="flex flex-col gap-0.5 pt-3">
        {signatureUrl ? (
          // The ink is dark, as it goes on the PDF: on the screen's colors it needs its paper.
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={signatureUrl}
            alt="Tu firma"
            className={cn(
              "mb-1 h-12 max-w-44 self-start object-contain object-left-bottom",
              !paper && "rounded-md bg-paper px-1.5 py-1",
            )}
          />
        ) : signed ? (
          <p className={cn("text-badge font-normal", look.muted)}>Firmada</p>
        ) : (
          <hr aria-hidden className={cn("mt-6 mb-1 w-40", look.signHere)} />
        )}
        <p className="text-section font-semibold break-words">{issuer.name}</p>
        {issuer.document_number && (
          <p className={cn("text-support", look.muted)}>
            {DOCUMENT_TYPE_LABELS[issuer.document_type]} {issuer.document_number}
          </p>
        )}
      </div>
      {paper && (
        // How each page of the PDF ends: its number and date, the page, and the house.
        <>
          <div
            className={cn(
              "flex justify-between gap-3 border-t pt-2 text-badge font-normal",
              look.rule,
              look.muted,
            )}
          >
            <span>
              {formatBillNumber(number)} · {formatDate(issueDate)}
            </span>
            <span>Página 1 de 1</span>
          </div>
          <BrandMark tone="ink" className="h-4.5 self-center" />
        </>
      )}
    </section>
  );
}
