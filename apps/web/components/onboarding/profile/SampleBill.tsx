"use client";

import { BillDocument } from "@/components/bills/BillDocument";
import { useSignatureUrl } from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";
import { formatMonth, todayInBogota } from "@/lib/format";

type Settings = components["schemas"]["SettingsResponse"];

const RENT = 1_450_000;
const pad = (n: number) => String(n).padStart(2, "0");

/**
 * The owner's first bill as it will look, with what they have filled in so far: the
 * owner's part is theirs; the tenant and the rent are an example. It goes out next month,
 * on the owner's send day.
 */
export function SampleBill({ settings }: { settings: Settings }) {
  const { data: signature } = useSignatureUrl(settings.has_signature);
  const [year, month] = todayInBogota().split("-").map(Number);
  const next = month === 12 ? `${year + 1}-01` : `${year}-${pad(month + 1)}`;
  // An example tenant pays the 5th, or a few days after the bill if it goes out later.
  const due = Math.min(28, Math.max(5, settings.send_day + 4));

  return (
    <div className="flex flex-col gap-2">
      <BillDocument
        number={1}
        issueDate={`${next}-${pad(settings.send_day)}`}
        issuer={settings}
        tenant={{ name: "Marta Ríos", document_type: "cc", document_number: "1.020.334.556" }}
        items={[{ description: "Canon de arrendamiento", amount: RENT }]}
        ofTheRent={`${formatMonth(`${next}-01`)} · Apto 101`}
        total={RENT}
        dueDate={`${next}-${pad(due)}`}
        signed={settings.has_signature}
        signatureUrl={signature?.url}
        paper
      />
      <p className="text-center text-support text-muted-foreground">
        El arrendatario y el canon son de ejemplo.
      </p>
    </div>
  );
}
