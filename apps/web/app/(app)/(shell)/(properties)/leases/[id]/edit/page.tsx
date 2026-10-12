import type { Metadata } from "next";

import { EditLeaseScreen } from "@/components/leases/LeaseEditor";

export const metadata: Metadata = { title: "Editar contrato · Arrendi" };

export default async function EditLeasePage({ params }: PageProps<"/leases/[id]/edit">) {
  const { id } = await params;
  return <EditLeaseScreen leaseId={id} />;
}
