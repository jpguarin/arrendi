import type { Metadata } from "next";

import { PropertiesScreen } from "@/components/properties/PropertiesScreen";

export const metadata: Metadata = { title: "Inmuebles · Arrendi" };

export default function PropertiesPage() {
  return <PropertiesScreen />;
}
