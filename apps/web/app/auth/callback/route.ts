import { NextResponse, type NextRequest } from "next/server";

import { safeNextPath } from "@/lib/navigation";
import { createClient } from "@/lib/supabase/server";

// Where Google sends the owner back after signing in. It only turns the code into a
// session; there are no business rules here.
export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const code = searchParams.get("code");
  const next = safeNextPath(searchParams.get("next"));

  let signedIn = false;
  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    signedIn = !error;
  }

  // Without a code, the owner cancelled at Google or Google reported an error.
  const destination = signedIn ? next : "/login?error=google_failed";
  return NextResponse.redirect(new URL(destination, request.url));
}
