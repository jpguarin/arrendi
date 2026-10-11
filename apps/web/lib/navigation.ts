/** A path inside the app to continue to, or the home screen if it is anything else. */
export function safeNextPath(next: string | null): string {
  // Only our own paths: never `//other.site` or `/\other.site`, which leave the app.
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\")) {
    return "/";
  }
  return next;
}
