import { NextResponse, type NextRequest } from "next/server";

import { updateSession, withSession } from "@/lib/supabase/proxy";

// Screens for people who are not signed in.
const SIGNED_OUT_ONLY = ["/login", "/signup", "/reset-password"];
// Open to everyone: the links that come back from an email or from Google, and what
// the installed app needs before anyone signs in.
const PUBLIC_PREFIXES = ["/auth/", "/serwist/", "/~offline", "/manifest.webmanifest"];

export async function proxy(request: NextRequest) {
  const { response, signedIn } = await updateSession(request);
  const { pathname } = request.nextUrl;

  if (PUBLIC_PREFIXES.some((prefix) => pathname.startsWith(prefix))) return response;

  const signedOutOnly = SIGNED_OUT_ONLY.includes(pathname);
  if (!signedIn && !signedOutOnly) {
    return withSession(NextResponse.redirect(new URL("/login", request.url)), response);
  }
  if (signedIn && signedOutOnly) {
    return withSession(NextResponse.redirect(new URL("/", request.url)), response);
  }
  return response;
}

export const config = {
  // Everything except the API (FastAPI checks the token itself) and static files.
  matcher: ["/((?!api/|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|webp|ico)$).*)"],
};
