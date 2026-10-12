import type { Metadata } from "next";

import { NewLeaseScreen } from "@/components/leases/LeaseEditor";

export const metadata: Metadata = { title: "Nuevo contrato · Arrendi" };

export default async function NewLeasePage({ searchParams }: PageProps<"/leases/new">) {
  const { unit } = await searchParams;
  return <NewLeaseScreen unitId={typeof unit === "string" ? unit : undefined} />;
}
