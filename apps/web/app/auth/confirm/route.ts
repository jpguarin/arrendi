import type { EmailOtpType } from "@supabase/supabase-js";
import { NextResponse, type NextRequest } from "next/server";

import { safeNextPath } from "@/lib/navigation";
import { createClient } from "@/lib/supabase/server";

// Where the links in Supabase's emails land (confirm the email, reset the password).
// It only turns the link into a session; there are no business rules here.
export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const tokenHash = searchParams.get("token_hash");
  const type = searchParams.get("type") as EmailOtpType | null;
  const code = searchParams.get("code");
  const next = safeNextPath(searchParams.get("next"));

  const supabase = await createClient();
  let confirmed = false;
  if (tokenHash && type) {
    // The email templates send this: it works even if the link opens in another browser.
    const { error } = await supabase.auth.verifyOtp({ token_hash: tokenHash, type });
    confirmed = !error;
  } else if (code) {
    // Supabase's default templates send this: it only works in the browser that asked.
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    confirmed = !error;
  }

  const destination = confirmed ? next : "/login?error=invalid_link";
  return NextResponse.redirect(new URL(destination, request.url));
}
