import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { dashboardAuthConfig, SESSION_COOKIE, verifySessionToken } from "@/lib/session";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const resources = new Set(["stats", "conversations", "dealers", "loan-health"]);

export async function GET(
  request: NextRequest,
  { params }: { params: { resource: string } },
) {
  const config = dashboardAuthConfig();
  const token = cookies().get(SESSION_COOKIE)?.value;
  const session = await verifySessionToken(token, config.secret);
  if (!session || !token) {
    return NextResponse.json({ error: "Authentication required" }, { status: 401 });
  }
  if (!resources.has(params.resource)) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  const apiBase = (process.env.HARVESTOS_API_URL ?? "http://localhost:8000").replace(/\/+$/u, "");
  const upstreamUrl = new URL(`/api/${params.resource}`, apiBase);
  if (params.resource === "conversations") {
    const limit = Number(request.nextUrl.searchParams.get("limit") ?? 50);
    upstreamUrl.searchParams.set("limit", String(Number.isFinite(limit) ? Math.min(200, Math.max(1, limit)) : 50));
  }

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
