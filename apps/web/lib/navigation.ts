// Never reaches the network: it only gives the parser an origin to compare against.
const SAME_ORIGIN = "https://arrendi.invalid";

/** A path inside the app to continue to, or the home screen if it is anything else. */
export function safeNextPath(next: string | null): string {
  if (!next || !next.startsWith("/")) return "/";
  // A URL parser drops tabs and line breaks and reads `\` as `/`, so what looks like a path
  // here can leave the app later: `/<tab>/other.site` ends up as `//other.site`.
  if (/[\u0000-\u001f\u007f\\]/.test(next)) return "/";
  try {
    const url = new URL(next, SAME_ORIGIN);
    return url.origin === SAME_ORIGIN ? `${url.pathname}${url.search}${url.hash}` : "/";
  } catch {
    return "/";
  }
}

// The links Arrendi's emails carry: confirming a sign-up, resetting a password, accepting
// an invitation. `signup` is the older name of `email`.
const CONFIRMABLE_OTP_TYPES = ["email", "signup", "recovery", "invite"] as const;

export type ConfirmableOtpType = (typeof CONFIRMABLE_OTP_TYPES)[number];

export function isConfirmableOtpType(type: string | null): type is ConfirmableOtpType {
  return (CONFIRMABLE_OTP_TYPES as readonly (string | null)[]).includes(type);
}
