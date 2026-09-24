"use client";

import { FormEvent, useState } from "react";
import "./auth.css";

export default function LoginPage() {
  const [email, setEmail] = useState(
    process.env.NODE_ENV === "production" ? "" : "partner@harvestos.local",
  );
  const [password, setPassword] = useState("");
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const result = (await response.json()) as { error?: string };
      if (!response.ok) {
        setError(result.error ?? "We couldn’t sign you in. Please try again.");
        return;
      }
      const requested = new URLSearchParams(window.location.search).get("next") ?? "/";
      const destination = new URL(requested, window.location.origin);
      window.location.assign(
        destination.origin === window.location.origin
          ? `${destination.pathname}${destination.search}${destination.hash}`
          : "/",
      );
    } catch {
      setError("We couldn’t reach sign-in. Check your connection and try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-story" aria-label="About HarvestOS">
        <a className="auth-brand" href={process.env.NEXT_PUBLIC_LANDING_URL ?? "http://localhost:3000"}>
          <span className="brand-mark">h</span><span>harvest<span>os</span></span>
        </a>
        <div className="story-content">
          <p className="auth-eyebrow"><i /> PARTNER OPERATIONS</p>
          <h1>Better support<br />for every <em>growing</em><br />season.</h1>
          <p className="story-copy">A connected view of the conversations, local supply, and payment plans moving through your farmer network.</p>
          <div className="story-journey" aria-label="Journey channels">
            <span>SMS</span><i>→</i><span>WhatsApp</span><i>→</i><span>RCS</span><i>→</i><span>Email</span>
          </div>
        </div>
        <div className="auth-story-footer"><span>BUILT FOR THE PEOPLE BEHIND EVERY HARVEST</span><span>01 — PARTNER ACCESS</span></div>
        <div className="story-seal" aria-hidden="true"><span>H</span><i /></div>
      </section>

      <section className="auth-main">
        <a className="back-link" href={process.env.NEXT_PUBLIC_LANDING_URL ?? "http://localhost:3000"}>← <span>Back to HarvestOS</span></a>
        <div className="auth-card-wrap">
          <div className="auth-card-heading"><span className="auth-kicker">YOUR WORKSPACE</span><h2>Welcome back.</h2><p>Sign in to continue to partner operations.</p></div>
          <form className="auth-form" onSubmit={signIn}>
            <label htmlFor="email">Work email</label>
            <div className="input-wrap"><span aria-hidden="true">✉</span><input id="email" name="email" type="email" autoComplete="username" inputMode="email" placeholder="you@organization.org" value={email} onChange={(event) => setEmail(event.target.value)} required maxLength={254} /></div>
            <div className="password-label"><label htmlFor="password">Password</label><span>Workspace credentials</span></div>
            <div className="input-wrap"><span aria-hidden="true">⌑</span><input id="password" name="password" type={visible ? "text" : "password"} autoComplete="current-password" placeholder="Enter your password" value={password} onChange={(event) => setPassword(event.target.value)} required maxLength={1024} /><button type="button" className="password-toggle" onClick={() => setVisible(!visible)} aria-label={visible ? "Hide password" : "Show password"}>{visible ? "Hide" : "Show"}</button></div>
            {error && <div className="auth-error" role="alert"><span>!</span>{error}</div>}
            <button className="sign-in-button" type="submit" disabled={busy}>{busy ? <><span className="spinner"/> Verifying your access…</> : <>Sign in to your workspace <span>→</span></>}</button>
          </form>
          <div className="auth-support"><span className="support-lock">⌑</span><p>Your account protects partner and farmer information.<br/><b>Need access?</b> Ask your workspace administrator.</p></div>
          {process.env.NODE_ENV !== "production" && <details className="dev-credentials"><summary>Local demo credentials</summary><p>Email <code>partner@harvestos.local</code><br/>Password <code>HarvestDemo!2026</code></p></details>}
        </div>
        <footer className="auth-footer"><span>© {new Date().getFullYear()} HARVESTOS</span><span><a href={`${process.env.NEXT_PUBLIC_LANDING_URL ?? "http://localhost:3000"}/#architecture`}>System design</a><i/> SECURE PARTNER ACCESS</span></footer>
      </section>
    </main>
  );
}
