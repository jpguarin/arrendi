/**
 * The onboarding draft as it is kept on the device, so that a reload does not lose what
 * the owner typed. It is tied to the owner: someone else signing in on the same tab
 * starts from nothing.
 */

// Bumped when the shape of the draft changes: an older one is dropped, not misread.
const VERSION = 1;

export const DRAFT_KEY = "arrendi.onboarding";

type Stored = { version: number; owner: string; draft: unknown };

export function serializeDraft(draft: unknown, owner: string): string {
  return JSON.stringify({ version: VERSION, owner, draft } satisfies Stored);
}

/** The draft saved for this owner, or null if there is none that can be used. */
export function parseDraft<T>(raw: string | null, owner: string): T | null {
  if (!raw) return null;
  let stored: Partial<Stored>;
  try {
    stored = JSON.parse(raw);
  } catch {
    return null;
  }
  if (typeof stored !== "object" || stored === null) return null;
  if (stored.version !== VERSION || stored.owner !== owner || !stored.draft) return null;
  return stored.draft as T;
}
