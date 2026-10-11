"use client";

import { useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useMemo, useState } from "react";

import type { LeaseValues } from "@/components/leases/LeaseForm";
import type { PropertyValues } from "@/components/properties/PropertyForm";
import { api } from "@/lib/api/client";
import type { UnitUse } from "@/lib/labels";

export type UnitDraft = { name: string; use: UnitUse };

type Draft = {
  property?: PropertyValues;
  units?: UnitDraft[];
  lease?: Partial<LeaseValues>;
};

type OnboardingContextValue = {
  draft: Draft;
  update: (changes: Draft) => void;
};

const OnboardingContext = createContext<OnboardingContextValue | null>(null);

/**
 * What the owner has filled in so far. It lives in memory while they move between the
 * three steps, and nothing is saved until the last one: the API creates it all at once.
 */
export function OnboardingProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [draft, setDraft] = useState<Draft>({});

  // The onboarding happens once. Someone who already has a property and lands here
  // (an old link, the back button) goes home; the API would reject it anyway.
  useEffect(() => {
    api
      .GET("/api/me")
      .then(({ data }) => {
        if (data?.onboarding_complete) router.replace("/");
      })
      .catch(() => {});
  }, [router]);

  const value = useMemo(
    () => ({ draft, update: (changes: Draft) => setDraft((old) => ({ ...old, ...changes })) }),
    [draft],
  );
  return <OnboardingContext.Provider value={value}>{children}</OnboardingContext.Provider>;
}

export function useOnboarding(): OnboardingContextValue {
  const value = useContext(OnboardingContext);
  if (!value) throw new Error("useOnboarding must be used inside OnboardingProvider");
  return value;
}
