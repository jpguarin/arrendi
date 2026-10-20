"use client";

import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import type { LeaseValues } from "@/components/leases/LeaseForm";
import type { PropertyValues } from "@/components/properties/PropertyForm";
import { useMe } from "@/lib/api/queries";
import type { UnitUse } from "@/lib/labels";
import { DRAFT_KEY, parseDraft, serializeDraft } from "@/lib/onboarding-draft";

export type UnitDraft = { name: string; use: UnitUse };

export type Draft = {
  /** What "Continuar" confirmed: the summary shows it and the API gets it. */
  property?: PropertyValues;
  units?: UnitDraft[];
  /** What is being typed in a part that is open, kept so a reload does not lose it. */
  propertyInput?: Partial<PropertyValues>;
  unitsInput?: UnitDraft[];
  lease?: Partial<LeaseValues>;
  /** Whether the first lease is created now or added later from its unit. */
  withLease: boolean;
};

/** What happened when everything was created, for the closing screen. */
export type Outcome = { leaseCreated: boolean; documentFailed: boolean; inventoryFailed: boolean };

type OnboardingContextValue = {
  draft: Draft;
  update: (changes: Partial<Draft>) => void;
  /** False until the draft saved on the device has been read. */
  ready: boolean;
  /** The signed lease picked so far. A file cannot be saved on the device. */
  file: File | null;
  setFile: (file: File | null) => void;
  /** The same, for the inventory of the unit. */
  inventory: File | null;
  setInventory: (file: File | null) => void;
  /** While the API creates everything: the button that started it waits. */
  creating: boolean;
  setCreating: (creating: boolean) => void;
  outcome: Outcome | null;
  /** Everything was created: the draft leaves the device, the closing screen shows it. */
  finish: (outcome: Outcome) => void;
};

const OnboardingContext = createContext<OnboardingContextValue | null>(null);

const EMPTY: Draft = { withLease: true };

function readStorage(): string | null {
  try {
    return sessionStorage.getItem(DRAFT_KEY);
  } catch {
    return null;
  }
}

function writeStorage(value: string | null) {
  try {
    if (value === null) sessionStorage.removeItem(DRAFT_KEY);
    else sessionStorage.setItem(DRAFT_KEY, value);
  } catch {
    // Without storage the draft lives in memory only, as it did before.
  }
}

/**
 * What the owner has filled in so far. Nothing reaches the API until the end: it creates
 * it all at once. Meanwhile the draft is kept in this tab, so a reload does not lose it.
 */
export function OnboardingProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { data: me } = useMe();
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [loadedFor, setLoadedFor] = useState<string>();
  const [file, setFile] = useState<File | null>(null);
  const [inventory, setInventory] = useState<File | null>(null);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [creating, setCreating] = useState(false);
  const ready = me !== undefined && loadedFor === me.id;

  // Read once the owner is known: a draft belongs to whoever typed it.
  useEffect(() => {
    if (!me || loadedFor === me.id) return;
    const saved = parseDraft<Draft>(readStorage(), me.id);
    // eslint-disable-next-line react-hooks/set-state-in-effect -- the device is only readable after mounting
    if (saved) setDraft({ ...EMPTY, ...saved });
    setLoadedFor(me.id);
  }, [me, loadedFor]);

  useEffect(() => {
    if (ready && !outcome && me) writeStorage(serializeDraft(draft, me.id));
  }, [draft, ready, outcome, me]);

  // The onboarding happens once. Someone who already has a property and lands here
  // (an old link, the back button, a reload of the closing screen) goes home; the API
  // would reject it anyway.
  const done = me?.onboarding_complete === true && !outcome;
  useEffect(() => {
    if (done) router.replace("/");
  }, [done, router]);

  // Stable, so the forms can hand it what is typed without resubscribing.
  const update = useCallback(
    (changes: Partial<Draft>) => setDraft((old) => ({ ...old, ...changes })),
    [],
  );

  const value = useMemo<OnboardingContextValue>(
    () => ({
      draft,
      update,
      ready,
      file,
      setFile,
      inventory,
      setInventory,
      creating,
      setCreating,
      outcome,
      finish: (result) => {
        writeStorage(null);
        setOutcome(result);
      },
    }),
    [draft, update, ready, file, inventory, creating, outcome],
  );
  return <OnboardingContext.Provider value={value}>{children}</OnboardingContext.Provider>;
}

export function useOnboarding(): OnboardingContextValue {
  const value = useContext(OnboardingContext);
  if (!value) throw new Error("useOnboarding must be used inside OnboardingProvider");
  return value;
}
