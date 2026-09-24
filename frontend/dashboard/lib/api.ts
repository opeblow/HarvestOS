const API_BASE = "/api/dashboard";

export type Stats = {
  sessions: number;
  messages: number;
  channel_messages: Record<string, number>;
  diagnoses: number;
  quotes: number;
  loans_issued: number;
  reservations: number;
  notifications: number;
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

export type NotificationItem = {
  id: string;
  recipient: string;
  channel: string;
  category: string;
  title: string;
  body: string;
  entity: Record<string, unknown>;
  created_ts: string;
  read_ts: string | null;
  delivered_externally: boolean;
  external_provider: string;
};

export type NotificationPage = {
  items: NotificationItem[];
  unread: number;
  total: number;
};

async function getJson<T>(path: string, signal: AbortSignal): Promise<T> {
  const resp = await fetch(path, {
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

export function fetchNotifications(limit: number, signal: AbortSignal) {
  return getJson<NotificationPage>(`${API_BASE}/notifications?limit=${limit}`, signal);
}

export async function markNotificationRead(id: string): Promise<void> {
  const resp = await fetch(`${API_BASE}/notifications/${encodeURIComponent(id)}/read`, {
    method: "POST",
    headers: { Accept: "application/json" },
  });
  if (!resp.ok) {
    throw new Error(`mark read returned ${resp.status}`);
  }
}

export async function markAllNotificationsRead(): Promise<void> {
  const resp = await fetch(`${API_BASE}/notifications/read-all`, {
    method: "POST",
    headers: { Accept: "application/json" },
  });
  if (!resp.ok) {
    throw new Error(`read all returned ${resp.status}`);
  }
}
