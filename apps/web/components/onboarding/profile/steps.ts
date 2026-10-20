import type { components } from "@/lib/api/schema";

type Settings = components["schemas"]["SettingsResponse"];

// "Tus datos", before the first property: four questions, one per screen, and a review.

export const QUESTIONS = ["document", "payment", "signature", "send-day"] as const;
export type Question = (typeof QUESTIONS)[number];
export type ProfileStep = Question | "review";

export const PROFILE_STEPS: readonly ProfileStep[] = [...QUESTIONS, "review"];

export const isProfileStep = (value: string): value is ProfileStep =>
  (PROFILE_STEPS as readonly string[]).includes(value);

export const profileHref = (step: ProfileStep) => `/onboarding/profile/${step}`;

export const nextStep = (step: ProfileStep): ProfileStep =>
  PROFILE_STEPS[Math.min(PROFILE_STEPS.indexOf(step) + 1, PROFILE_STEPS.length - 1)];

/**
 * The first question whose answer the bill still lacks, or null with all of them. The send
 * day always has one, so it is never what is missing.
 */
export function firstUnanswered(settings: Settings): Question | null {
  if (!settings.document_number) return "document";
  if (!settings.payment_details) return "payment";
  if (!settings.has_signature) return "signature";
  return null;
}

/** Whether the step can open: never past the first question still unanswered. */
export function canOpen(step: ProfileStep, settings: Settings): boolean {
  const missing = firstUnanswered(settings);
  return missing === null || PROFILE_STEPS.indexOf(step) <= PROFILE_STEPS.indexOf(missing);
}
