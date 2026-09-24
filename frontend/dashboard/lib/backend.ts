import { cookies } from "next/headers";
import { dashboardAuthConfig, SESSION_COOKIE, verifySessionToken } from "@/lib/session";

export function apiBase(): string {
  return (process.env.HARVESTOS_API_URL ?? "http://localhost:8000").replace(/\/+$/u, "");
}

export async function sessionToken(): Promise<string | null> {
  const config = dashboardAuthConfig();
  const token = cookies().get(SESSION_COOKIE)?.value;
  if (!token) return null;
  const session = await verifySessionToken(token, config.secret);
  return session ? token : null;
}
