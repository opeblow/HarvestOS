"use client";

import { useCallback, useEffect, useState } from "react";
import "./console.css";
import {
  type ConversationRow, type Dealer, type LoanHealth, type Stats,
  fetchConversations, fetchDealers, fetchLoanHealth, fetchStats,
} from "@/lib/api";

const money = new Intl.NumberFormat("en-NG", { maximumFractionDigits: 0 });

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [conversations, setConversations] = useState<ConversationRow[]>([]);
  const [dealers, setDealers] = useState<Dealer[]>([]);
  const [loans, setLoans] = useState<LoanHealth | null>(null);
  const [online, setOnline] = useState(false);
  const [updated, setUpdated] = useState<Date | null>(null);
  const [query, setQuery] = useState("");

  async function signOut() {
    await fetch("/api/auth/logout", { method: "POST" });
    window.location.replace("/login");
  }

  const refresh = useCallback(async (signal: AbortSignal) => {
    try {
      const [nextStats, nextConversations, nextDealers, nextLoans] = await Promise.all([
        fetchStats(signal), fetchConversations(50, signal), fetchDealers(signal), fetchLoanHealth(signal),
      ]);
      setStats(nextStats); setConversations(nextConversations); setDealers(nextDealers);
      setLoans(nextLoans); setOnline(true); setUpdated(new Date());
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError")) setOnline(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void refresh(controller.signal);
    const timer = window.setInterval(() => void refresh(controller.signal), 10000);
    return () => { controller.abort(); window.clearInterval(timer); };
  }, [refresh]);

  const filtered = conversations.filter((row) =>
    `${row.phone} ${row.last_message} ${row.diagnosis_issue} ${row.channel}`.toLowerCase().includes(query.toLowerCase()),
  );
  const channelRows = Object.entries(stats?.channel_messages ?? {}).sort((a, b) => b[1] - a[1]);
  const maxChannel = Math.max(1, ...channelRows.map(([, count]) => count));

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#overview" aria-label="HarvestOS home"><span className="brand-mark">h</span><span>harvest<span className="brand-light">os</span></span></a>
        <div className="workspace"><span className="workspace-icon">P</span><span><b>Partner demo network</b><small>Sample workspace</small></span><span className="chevron">⌄</span></div>
        <p className="nav-label">WORKSPACE</p>
        <nav className="nav-list" aria-label="Main navigation">
          <a className="nav-item active" href="#overview"><span>◫</span> Overview <span className="nav-dot" /></a>
          <a className="nav-item" href="#conversations"><span>☷</span> Conversations <span className="nav-count">{stats?.sessions ?? 0}</span></a>
          <a className="nav-item" href="#network"><span>⌖</span> Dealer network</a>
          <a className="nav-item" href="#impact"><span>↗</span> Impact & finance</a>
        </nav>
        <div className="sidebar-bottom"><div className="help-card"><span className="help-icon">✳</span><b>Field notes</b><p>One session follows each farmer across the journey.</p><a href="#conversations">See recent journeys ↗</a></div><div className="profile"><span className="avatar">DE</span><span><b>Demo workspace</b><small>Local operations view</small></span><span className="chevron">···</span></div></div>
      </aside>

      <main className="main-area" id="overview">
        <header className="topbar"><div className="breadcrumbs">Workspace <span>/</span> <b>Overview</b></div><div className="top-actions"><span className={`connection ${online ? "is-online" : ""}`}><i />{online ? "Systems operational" : "API unavailable"}</span><button className="icon-button" aria-label="Notifications">♧<i /></button><button className="sign-out-button" onClick={signOut}>Sign out</button></div></header>
        <div className="content-wrap">
          <section className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line" /> FIELD OPERATIONS <span className="date-label">· {new Intl.DateTimeFormat("en", { weekday: "long", month: "long", day: "numeric" }).format(new Date())}</span></div><h1>Your network, in focus<span>.</span></h1><p className="lede">Here’s what’s happening across your farmer network.</p></div><button className="export-button" onClick={() => window.print()}><span>↓</span> Export report</button></section>

          {!online && <div className="offline-banner"><span>!</span><div><b>Showing your last available view</b><p>Couldn’t reach the HarvestOS API. Start the backend at localhost:8000 to see live operations.</p></div><button onClick={() => { const controller = new AbortController(); void refresh(controller.signal); }}>Retry ↻</button></div>}

          <section className="metric-grid" aria-label="Network metrics">
            <Metric label="Farmers reached" value={stats?.sessions.toLocaleString() ?? "—"} delta="Across active sessions" icon="♧" tone="green" />
            <Metric label="Messages handled" value={stats?.messages.toLocaleString() ?? "—"} delta={`${channelRows.length} active channels`} icon="↗" tone="gold" />
            <Metric label="Crop issues assessed" value={stats?.diagnoses.toLocaleString() ?? "—"} delta="Diagnosis journeys" icon="⌁" tone="blue" />
            <Metric label="Input orders" value={stats?.reservations.toLocaleString() ?? "—"} delta="Reservations created" icon="◉" tone="coral" />
          </section>

          <section className="insight-grid" id="impact">
          <article className="panel impact-panel"><div className="panel-heading"><div><p className="section-kicker">NETWORK IMPACT</p><h2>Support that moves the harvest.</h2></div><span className="live-label">LIVE TOTALS</span></div><div className="impact-body"><div className="impact-number"><span>₦</span>{loans ? money.format(loans.portfolio_ngn) : "—"}<small>financing facilitated</small></div><div className="impact-foot"><span className="impact-glyph">↗</span><span><b>{loans?.active_loans ?? "—"}</b> active payment plans</span><span className="foot-note">Across your network</span></div><div className="impact-summary"><span className="summary-icon">✳</span><span>Every assessment, reservation, and payment plan comes from a connected farmer session.</span></div></div></article>

            <article className="panel channel-panel"><div className="panel-heading"><div><p className="section-kicker">CONVERSATION MIX</p><h2>Meet farmers where they are.</h2></div><button className="more-button" aria-label="More channel options">···</button></div><div className="channel-total"><b>{stats?.messages.toLocaleString() ?? "—"}</b><span>messages across channels</span></div><div className="channel-bars">{channelRows.length ? channelRows.map(([name, count]) => <div className="channel-row" key={name}><span className={`channel-icon ${name}`}>{name === "sms" ? "▤" : name === "whatsapp" ? "◉" : name === "rcs" ? "▧" : "✉"}</span><div className="channel-detail"><div><b>{name.toUpperCase()}</b><span>{count}</span></div><div className="bar-track"><i style={{ width: `${Math.max(3, count / maxChannel * 100)}%` }} /></div></div></div>) : <p className="empty-inline">Channel activity will appear once messages arrive.</p>}</div><div className="channel-caption"><span className="legend-dot"/> Message volume <span>Live session totals</span></div></article>
          </section>

          <section className="lower-grid"><article className="panel conversation-panel" id="conversations"><div className="panel-heading conversation-heading"><div><p className="section-kicker">FARMER SUPPORT</p><h2>Recent conversations <span className="count-pill">{conversations.length}</span></h2></div><div className="table-actions"><label className="search-box"><span>⌕</span><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Find a conversation" aria-label="Find a conversation"/><kbd>⌘ K</kbd></label><button className="filter-button">Filter <span>☷</span></button></div></div><div className="table-scroll"><table><thead><tr><th>FARMER</th><th>LAST MESSAGE</th><th>JOURNEY STAGE</th><th>CHANNELS</th><th>UPDATED</th></tr></thead><tbody>{filtered.slice(0, 8).map((row, index) => <tr key={`${row.phone}-${index}`}><td><div className="farmer-cell"><span className={`farmer-avatar avatar-${index % 4}`}>{["AB", "YK", "FM", "SA"][index % 4]}</span><span><b>{row.phone}</b><small>{row.diagnosis_issue || row.order_status || (row.has_loan ? "Payment plan active" : "Farmer network")}</small></span></div></td><td className="message-cell">{row.last_message || "Conversation started"}</td><td><Stage row={row}/></td><td><div className="channel-pills">{row.visited_channels.slice(0, 3).map((channel) => <span key={channel}>{channel}</span>)}</div></td><td className="time-cell">{relativeTime(row.last_ts)}</td></tr>)}{filtered.length === 0 && <tr><td colSpan={5}><div className="empty-state"><span>⌕</span><b>{query ? "No matching conversations" : "Your farmer network is ready"}</b><p>{query ? "Try another name, issue, or channel." : "New farmer conversations will appear here as they arrive."}</p></div></td></tr>}</tbody></table></div><div className="table-footer"><span>Showing <b>{Math.min(filtered.length, 8)}</b> of <b>{filtered.length}</b> conversations</span><a href="#conversations">View all conversations <span>→</span></a></div></article>

          <article className="panel dealer-panel" id="network"><div className="panel-heading"><div><p className="section-kicker">SUPPLY NETWORK</p><h2>Dealer partners <span className="count-pill">{dealers.length}</span></h2></div><button className="more-button" aria-label="More dealer options">···</button></div><div className="dealer-list">{dealers.slice(0, 5).map((dealer, index) => <div className="dealer-row" key={dealer.name}><span className={`dealer-mark dealer-${index % 4}`}>{dealer.name.slice(0, 1)}</span><span className="dealer-info"><b>{dealer.name}</b><small>{dealer.state} · {dealer.stock.length} stocked lines</small></span><span className="dealer-status"><i/> Active</span></div>)}{dealers.length === 0 && <div className="empty-state compact"><span>⌖</span><b>Dealer network is warming up</b><p>Verified local partners will show up here.</p></div>}</div><a className="dealer-link" href="#network">Explore dealer network <span>→</span></a></article></section>

          <footer className="page-footer"><span>HARVESTOS <i>·</i> PARTNER OPERATIONS</span><span>{updated ? `Updated ${updated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}` : "Waiting for first sync"} <i className={online ? "footer-live" : ""}/></span></footer>
        </div>
      </main>
    </div>
  );
}

function Metric({ label, value, delta, icon, tone }: { label: string; value: string; delta: string; icon: string; tone: string }) {
  return <article className="metric-card"><div className={`metric-icon ${tone}`}>{icon}</div><p>{label}</p><strong>{value}</strong><span className="metric-note">{delta}</span></article>;
}

function Stage({ row }: { row: ConversationRow }) {
  const stage = row.stage.stage || row.order_status || (row.has_loan ? "Financing" : row.diagnosis_issue ? "Assessed" : "In conversation");
  const cls = row.order_status ? "complete" : row.has_loan ? "finance" : row.diagnosis_issue ? "assessed" : "progress";
  return <span className={`stage-chip ${cls}`}><i/>{stage.replaceAll("_", " ")}</span>;
}

function relativeTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Recently";
  const minutes = Math.max(0, Math.floor((Date.now() - date.getTime()) / 60000));
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}
