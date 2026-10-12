import type { Metadata } from "next";

import { EditUnitScreen } from "@/components/units/UnitEditor";

export const metadata: Metadata = { title: "Editar unidad · Arrendi" };

export default async function EditUnitPage({ params }: PageProps<"/units/[id]/edit">) {
  const { id } = await params;
  return <EditUnitScreen unitId={id} />;
}
