import { scrypt, timingSafeEqual } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import {
  createSessionToken,
  dashboardAuthConfig,
  SESSION_COOKIE,
  SESSION_TTL_SECONDS,
} from "@/lib/session";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const attempts = new Map<string, { count: number; resetAt: number }>();
const WINDOW_MS = 15 * 60 * 1000;
const MAX_ATTEMPTS = 8;

function requestIsSameOrigin(request: NextRequest) {
  const origin = request.headers.get("origin");
  try {
    return Boolean(origin && new URL(origin).host === request.headers.get("host"));
  } catch {
    return false;
  }
}

function derive(value: string) {
  return new Promise<Buffer>((resolve, reject) => {
    scrypt(value, "harvestos-login-comparison", 32, (error, result) => {
      if (error) reject(error);
      else resolve(result as Buffer);
    });
  });
}

async function safeEqual(left: string, right: string) {
  const [leftHash, rightHash] = await Promise.all([derive(left), derive(right)]);
  return timingSafeEqual(leftHash, rightHash);
}

export async function POST(request: NextRequest) {
  if (!requestIsSameOrigin(request)) {
    return NextResponse.json({ error: "Request origin could not be verified." }, { status: 403 });
  }

  const address = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "unknown";
  const now = Date.now();
  if (attempts.size > 1000) {
    for (const [key, value] of attempts) {
      if (value.resetAt <= now) attempts.delete(key);
    }
  }
  const attempt = attempts.get(address);
  if (attempt && attempt.resetAt > now && attempt.count >= MAX_ATTEMPTS) {
    return NextResponse.json(
      { error: "Too many attempts. Wait a few minutes, then try again." },
      { status: 429, headers: { "Retry-After": String(Math.ceil((attempt.resetAt - now) / 1000)) } },
    );
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Enter your email and password." }, { status: 400 });
  }
  const input = body as { email?: unknown; password?: unknown };
  if (
    typeof input.email !== "string" ||
    typeof input.password !== "string" ||
    input.email.length > 254 ||
    input.password.length > 1024
  ) {
    return NextResponse.json({ error: "Enter your email and password." }, { status: 400 });
  }

  const config = dashboardAuthConfig();
  if (!config.email || !config.password || config.secret.length < 32) {
    return NextResponse.json(
      { error: "Dashboard sign-in is not configured. Set the server authentication variables." },
      { status: 503 },
    );
  }

  const email = input.email.trim().toLowerCase();
  const [emailMatches, passwordMatches] = await Promise.all([
    safeEqual(email, config.email.trim().toLowerCase()),
    safeEqual(input.password, config.password),
  ]);
  const valid = emailMatches && passwordMatches;
  if (!valid) {
    const current = attempts.get(address);
    attempts.set(address, {
      count: current && current.resetAt > now ? current.count + 1 : 1,
      resetAt: current && current.resetAt > now ? current.resetAt : now + WINDOW_MS,
    });
    return NextResponse.json({ error: "That email and password combination was not recognized." }, { status: 401 });
  }

  attempts.delete(address);
  const token = await createSessionToken(config.email.trim().toLowerCase(), config.secret);
  const response = NextResponse.json({ ok: true });
  response.cookies.set(SESSION_COOKIE, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_TTL_SECONDS,
  });
  response.headers.set("Cache-Control", "no-store");
  return response;
}
