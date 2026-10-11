import type { Metadata } from "next";

import { BillScreen } from "@/components/bills/BillScreen";

export const metadata: Metadata = { title: "Cuenta de cobro · Arrendi" };

export default async function BillPage({ params }: PageProps<"/bills/[id]">) {
  const { id } = await params;
  return <BillScreen billId={id} />;
}
