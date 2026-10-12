import type { Metadata } from "next";

import { BillScreen } from "@/components/bills/BillScreen";

export const metadata: Metadata = { title: "Cuenta de cobro · Arrendi" };

export default async function BillPage({ params, searchParams }: PageProps<"/bills/[id]">) {
  const { id } = await params;
  const { proof } = await searchParams;
  return <BillScreen billId={id} proofFailed={proof === "failed"} />;
}
