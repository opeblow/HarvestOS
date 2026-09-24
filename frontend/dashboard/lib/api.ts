const API_BASE = "/api/dashboard";

export type Stats = {
  sessions: number;
  messages: number;
  channel_messages: Record<string, number>;
  diagnoses: number;
  quotes: number;
  loans_issued: number;
  reservations: number;
};

export type ConversationRow = {
  phone: string;
  channel: string;
  visited_channels: string[];
  last_message: string;
  last_ts: string;
  diagnosis_issue: string;
  order_status: string;
  has_loan: boolean;
  stage: Record<string, string>;
};

export type Dealer = {
  name: string;
  state: string;
  lat: number;
  lng: number;
  pickup_windows: string[];
  stock: DealerStock[];
};

export type DealerStock = {
  sku: string;
  product: string;
  price_ngn: number;
  qty: number;
};

export type LoanHealth = {
  active_loans: number;
  portfolio_ngn: number;
};

async function getJson<T>(path: string, signal: AbortSignal): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    signal,
    headers: { Accept: "application/json" },
  });
  if (!resp.ok) {
    throw new Error(`${path} returned ${resp.status}`);
  }
  return (await resp.json()) as T;
}

export function fetchStats(signal: AbortSignal) {
  return getJson<Stats>(`${API_BASE}/stats`, signal);
}

export function fetchConversations(limit: number, signal: AbortSignal) {
  return getJson<ConversationRow[]>(`${API_BASE}/conversations?limit=${limit}`, signal);
}

export function fetchDealers(signal: AbortSignal) {
  return getJson<Dealer[]>(`${API_BASE}/dealers`, signal);
}

export function fetchLoanHealth(signal: AbortSignal) {
  return getJson<LoanHealth>(`${API_BASE}/loan-health`, signal);
}
