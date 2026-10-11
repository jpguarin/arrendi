import type { Metadata } from "next";

import { LeaseScreen } from "@/components/leases/LeaseScreen";

export const metadata: Metadata = { title: "Contrato · Arrendi" };

export default async function LeasePage({ params, searchParams }: PageProps<"/leases/[id]">) {
  const { id } = await params;
  const { document } = await searchParams;
  return <LeaseScreen leaseId={id} documentFailed={document === "failed"} />;
}
