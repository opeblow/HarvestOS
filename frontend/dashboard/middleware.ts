import { NextRequest, NextResponse } from "next/server";
import { dashboardAuthConfig, SESSION_COOKIE, verifySessionToken } from "@/lib/session";

export async function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const claims = await verifySessionToken(
    request.cookies.get(SESSION_COOKIE)?.value,
    dashboardAuthConfig().secret,
  );

  if (!claims) {
    if (pathname.startsWith("/api/")) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 });
    }
    const login = new URL("/login", request.url);
    login.searchParams.set("next", `${pathname}${search}`);
    return NextResponse.redirect(login);
  }

  if (pathname === "/login") return NextResponse.redirect(new URL("/", request.url));
  return NextResponse.next();
}

export const config = {
  matcher: ["/", "/login", "/api/dashboard/:path*"],
};
