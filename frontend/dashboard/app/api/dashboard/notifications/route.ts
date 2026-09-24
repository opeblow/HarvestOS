import { NextRequest, NextResponse } from "next/server";
import { apiBase, sessionToken } from "@/lib/backend";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const token = await sessionToken();
  if (!token) {
    return NextResponse.json({ error: "Authentication required" }, { status: 401 });
  }

  const limit = Number(request.nextUrl.searchParams.get("limit") ?? 50);
  const safeLimit = Number.isFinite(limit) ? Math.min(200, Math.max(1, limit)) : 50;
  const unreadOnly = request.nextUrl.searchParams.get("unread_only") === "true";

  const upstreamUrl = new URL("/api/notifications", apiBase());
  upstreamUrl.searchParams.set("limit", String(safeLimit));
  if (unreadOnly) upstreamUrl.searchParams.set("unread_only", "true");

  try {
    const upstream = await fetch(upstreamUrl, {
      headers: { Accept: "application/json", Authorization: `Bearer ${token}` },
      cache: "no-store",
      signal: AbortSignal.timeout(8000),
    });
    const body = await upstream.json();
    return NextResponse.json(body, {
      status: upstream.status,
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return NextResponse.json({ error: "HarvestOS API is unavailable" }, { status: 502 });
  }
}
