import { NextRequest, NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/session";

export async function POST(request: NextRequest) {
  const origin = request.headers.get("origin");
  let sameOrigin = false;
  try {
    sameOrigin = Boolean(origin && new URL(origin).host === request.headers.get("host"));
  } catch {
    sameOrigin = false;
  }
  if (!sameOrigin) {
    return NextResponse.json({ error: "Request origin could not be verified." }, { status: 403 });
  }
  const response = NextResponse.json({ ok: true });
  response.cookies.set(SESSION_COOKIE, "", {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  });
  response.headers.set("Cache-Control", "no-store");
  return response;
}
