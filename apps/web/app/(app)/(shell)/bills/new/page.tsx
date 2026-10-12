import type { Metadata } from "next";

import { NewBillScreen } from "@/components/bills/NewBillScreen";

export const metadata: Metadata = { title: "Nueva cuenta de cobro · Arrendi" };

export default async function NewBillPage({ searchParams }: PageProps<"/bills/new">) {
  const { lease } = await searchParams;
  return <NewBillScreen leaseId={typeof lease === "string" ? lease : undefined} />;
}
