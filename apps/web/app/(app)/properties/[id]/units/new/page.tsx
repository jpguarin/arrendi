import type { Metadata } from "next";

import { NewUnitScreen } from "@/components/units/UnitEditor";

export const metadata: Metadata = { title: "Nueva unidad · Arrendi" };

export default async function NewUnitPage({ params }: PageProps<"/properties/[id]/units/new">) {
  const { id } = await params;
  return <NewUnitScreen propertyId={id} />;
}
