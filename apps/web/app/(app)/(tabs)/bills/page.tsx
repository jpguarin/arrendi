import type { Metadata } from "next";

import { BillsScreen } from "@/components/bills/BillsScreen";

export const metadata: Metadata = { title: "Cuentas de cobro · Arrendi" };

export default async function BillsPage({ searchParams }: PageProps<"/bills">) {
  const { unit } = await searchParams;
  return <BillsScreen initialUnitId={typeof unit === "string" ? unit : undefined} />;
}
