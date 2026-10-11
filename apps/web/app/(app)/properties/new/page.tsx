import type { Metadata } from "next";

import { NewPropertyScreen } from "@/components/properties/PropertyEditor";

export const metadata: Metadata = { title: "Nuevo inmueble · Arrendi" };

export default function NewPropertyPage() {
  return <NewPropertyScreen />;
}
