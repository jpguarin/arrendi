import type { Metadata } from "next";

import { EditPropertyScreen } from "@/components/properties/PropertyEditor";

export const metadata: Metadata = { title: "Editar inmueble · Arrendi" };

export default async function EditPropertyPage({ params }: PageProps<"/properties/[id]/edit">) {
  const { id } = await params;
  return <EditPropertyScreen propertyId={id} />;
}
