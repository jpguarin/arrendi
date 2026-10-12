import type { Metadata } from "next";

import { PaymentScreen } from "@/components/bills/PaymentScreen";

export const metadata: Metadata = { title: "Registrar pago · Arrendi" };

export default async function PaymentPage({
  params,
  searchParams,
}: PageProps<"/bills/[id]/payment">) {
  const { id } = await params;
  const { from } = await searchParams;
  return <PaymentScreen billId={id} fromHome={from === "home"} />;
}
