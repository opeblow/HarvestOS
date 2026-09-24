export const SESSION_COOKIE = "harvestos_session";
export const SESSION_TTL_SECONDS = 60 * 60 * 8;

type SessionClaims = {
  sub: string;
  iss: "harvestos";
  aud: "partner-dashboard";
  iat: number;
  exp: number;
};

function decodeBase64Url(value: string): Uint8Array<ArrayBuffer> {
  const base64 = value.replaceAll("-", "+").replaceAll("_", "/");
  const binary = atob(base64 + "=".repeat((4 - (base64.length % 4)) % 4));
  const bytes = new Uint8Array(new ArrayBuffer(binary.length));
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}

function encodeBase64Url(value: Uint8Array): string {
  let binary = "";
  for (const byte of value) binary += String.fromCharCode(byte);
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/u, "");
}

async function signingKey(secret: string, usage: KeyUsage[]): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    usage,
  );
}

export async function createSessionToken(email: string, secret: string): Promise<string> {
  const now = Math.floor(Date.now() / 1000);
  const claims: SessionClaims = {
    sub: email,
    iss: "harvestos",
    aud: "partner-dashboard",
    iat: now,
    exp: now + SESSION_TTL_SECONDS,
  };
  const payload = encodeBase64Url(new TextEncoder().encode(JSON.stringify(claims)));
  const signature = await crypto.subtle.sign(
    "HMAC",
    await signingKey(secret, ["sign"]),
    new TextEncoder().encode(payload),
  );
  return `${payload}.${encodeBase64Url(new Uint8Array(signature))}`;
}

export async function verifySessionToken(
  token: string | undefined,
  secret: string | undefined,
): Promise<SessionClaims | null> {
  if (!token || !secret || secret.length < 32) return null;
  const [payload, signature, extra] = token.split(".");
  if (!payload || !signature || extra !== undefined) return null;

  try {
    const valid = await crypto.subtle.verify(
      "HMAC",
      await signingKey(secret, ["verify"]),
      decodeBase64Url(signature),
      new TextEncoder().encode(payload),
    );
    if (!valid) return null;
    const claims = JSON.parse(new TextDecoder().decode(decodeBase64Url(payload))) as SessionClaims;
    const now = Math.floor(Date.now() / 1000);
    if (
      claims.iss !== "harvestos" ||
      claims.aud !== "partner-dashboard" ||
      !claims.sub ||
      claims.exp <= now ||
      claims.iat > now + 60
    ) {
      return null;
    }
    return claims;
  } catch {
    return null;
  }
}

export function dashboardAuthConfig() {
  const development = process.env.NODE_ENV !== "production";
  return {
    email: process.env.HARVESTOS_AUTH_EMAIL ?? (development ? "partner@harvestos.local" : ""),
    password: process.env.HARVESTOS_AUTH_PASSWORD ?? (development ? "HarvestDemo!2026" : ""),
    secret:
      process.env.HARVESTOS_SESSION_SECRET ??
      (development ? "local-only-change-before-deploy-6cc35149b2d84c71" : ""),
  };
}
