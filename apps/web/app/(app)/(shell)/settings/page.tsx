import type { Metadata } from "next";

import { SettingsScreen } from "@/components/settings/SettingsScreen";

export const metadata: Metadata = { title: "Ajustes · Arrendi" };

export default function SettingsPage() {
  return (
    <div className="flex w-full max-w-2xl flex-1 flex-col">
      <SettingsScreen />
    </div>
  );
}
