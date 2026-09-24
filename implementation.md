# HarvestOS — Implementation Plan (from scratch to submission)

A step-by-step, phase-gated plan to take HarvestOS from an empty repo to a world-class,
fully demoable, hackathon-winning agentic commerce platform. Every phase has an explicit
"Definition of Done" gate. Do not move to the next phase until the current one's gate is met.

---

## 0. Ground Rules (read once, follow always)

1. **Secrets never touch git.** `.env` is git-ignored; all infrastructure secrets live in
   AWS Secrets Manager / SSM Parameter Store at deploy time.
2. **Everything is code.** Infra is AWS CDK (TypeScript). One `cdk deploy` builds the whole
   stack. Manual console clicks are only for things AWS has no API for (e.g. sandbox number
   approval).
3. **Drift is forbidden.** No ad-hoc resources created in the console that aren't in the CDK
   stack. If you click it, delete it or define it.
4. **Reproducible by a stranger.** `git clone && npm install && cdk deploy` must work on a
   fresh machine with only credentials in `.env`.
5. **Every journey is a scripted test** — Journey A/B/C must pass as automated tests before
   it is demoed live.
6. **Type-safe end to end.** TypeScript at every boundary. No `any` leaking from Lambda
   through CDS handlers to the agents.
7. **Cost aware.** CDS, Bedrock, and SES are not free. Every loop has a budget and a cap.

---

## 1. Environment & Keys

Current `.env` state and what is still needed.

### Have already
| Key | Status |
|---|---|
| `AWS_ACCESS_KEY_ID` | Present (IAdmin/home key — see §1.1) |
| `AWS_SECRET_ACCESS_KEY` | Present |
| `AWS_DEFAULT_REGION=us-east-1` | Present — correct region for Bedrock + CDS |
| `OPENAI_API_KEY` | Present (dev fallback only; PDF uses Bedrock FMs) |
| `PAYSTACK_SECRET_KEY` (test) | Present — BNPL/payments. Test mode is fine for the hackathon. |
| `PAYSTACK_PUBLIC_KEY` (test) | Present |

### 1.1 Security action required BEFORE writing code (do not skip)
Your real AWS keys have now been shared in this chat session and in a local file. Treat
them as burned:

1. Rotate the AWS keys in the IAM console immediately — delete `AKIAS4XBXP4K62ER2YNB` and
   create a new pair **narrowly scoped** to this project (see §3 least-privilege policy).
2. Confirm the new key is an **IAM user key**, not the root account key.
3. Add `.env` to `.gitignore` on day one (Step 2).
4. Never screenshot or paste the new keys into a chat tool again.

### 1.2 Keys that make sense to add to `.env`
| New key | Required? | Where to get it |
|---|---|---|
| `AWS_ACCOUNT_ID` | Recommended | Invite IAM → users → your user. Speeds up all CDK/bootstrap commands. |
| `NGROK_AUTHTOKEN` | Recommended (dev) | ngrok.com free account — local webhook testing for SMS/WhatsApp/SES without deploying |
| `META_WHATSAPP_ACCESS_TOKEN` | Optional | meta for developers → Apps → WhatsApp. Only needed if you call the WhatsApp Cloud API directly. Prefer AWS EUM Social instead (token handled by AWS). |
| `META_PHONE_NUMBER_ID` | Optional | Same app, phone number page. Same caveat as above. |
| `VERCEL_TOKEN` | Optional | Only if you push the frontend to Vercel instead of Amplify. |
| `SENTRY_DSN` | Recommended (prod) | sentry.io — error tracking in prod. Free tier. |
| `PAYSTACK_SECRET_KEY` (live) | Only at launch | dashboard.paystack.com → Settings → API Keys & Webhooks. Keep test keys for now. |

### 1.3 Non-key console prerequisites (no env variable — AWS console actions)
| Item | Where | Why |
|---|---|---|
| Enable Bedrock model access | Bedrock console → Model access → enable Claude + a vision model (e.g. Claude) in us-east-1 | Model access is per-account, per-region, manual. Do first; approval can lag. |
| Request EUM (SMS/RCS) sandbox number | End User Messaging console → sandbox | Needed even for testing. Request on day 1 — provisioning is the slowest dependency. |
| Request EUM Social (WhatsApp) test number | End User Messaging Social console | WhatsApp test number; real number needs Meta Business verification. |
| Verify an email identity in SES | SES console → Identities (or via CDK `ses.EmailIdentity`) | SMS/email webhooks ignore SES you can't send from. |
| AWS Budget alarm (hard $ cap) | Billing → Budgets (or CDK `aws_budgets`) | Prevents a runaway Bedrock/CDS bill. |

---

## 2. Repository Scaffolding

**Goal:** a clean monorepo matching the PDF's §10 layout, with hygiene and CI from byte one.

1. `git init && git add .gitignore` with:
   - `.env`, `.env.*`, `!.env.example`
   - `node_modules/`, `dist/`, `build/`, `.next/`, `cdk.out/`
   - `*.png` nav/debug temp files, `coverage/`
2. Create `.env.example` with the full documented key set (empty values) — the public contract
   for what the repo needs.
3. Create root `package.json` with workspaces: `backend`, `frontend/landing`,
   `frontend/dashboard`, `infra/cdk`. One `npm install` at root installs everything.
4. Root `tsconfig.base.json` shared by all workspaces — strict mode, `noUncheckedIndexedAccess`,
   `exactOptionalPropertyTypes`.
5. `README.md` — setup, run, demo, and architecture summary (this doubles as judge-facing docs).
6. GitHub repo → push → enable branch protection on `main`.
7. Set up **GitHub Actions**:
   - CI workflow: `npm ci && tsc --noEmit` (all workspaces) → `npm test` → `npx prettier --check` (or biome) → `eslint`.
   - Deploy workflow: on push to `main` → `cdk deploy` to staging, on tagged release → prod.
8. GitHub → Settings → Secrets: add the new (rotated) AWS keys + account id + any other env
   keys so CI/CD never touches a local `.env`.

**Gate:** fresh clone + `npm ci` passes CI locally, and a commit to `main` is deployable.

---

## 3. Infrastructure — AWS CDK (Phase: Weeks 1–2 start)

**Goal:** full stack defined as code, deployed with one command.

Order of construction (each layer is a separate CDK construct so it can be tested alone):

1. **Bootstrap:** `cdk bootstrap` once per account/region.
2. **Network & accounts:** VPC not required (all serverless); rely on Lambda-managed is fine
   for MVP. IAM **least-privilege** roles per service (Lambda role only touches its own table / S3 prefix / SES identity).
3. **Storage:**
   - `DynamoDB` single-table design keyed by `phoneNumber` (the identity key) + `sk`
     (session/conversation/message/loan sub-keys). GSIs: `channel+ts`, `agent+ts`,
     `dealerId`, `loanStatus`. Encryption: customer-managed KMS key.
   - `S3` bucket `harvestos-assets-<account>-<region>` with prefixes `photos/`, `pdfs/`;
     lifecycle + KMS encryption + block public access (served via signed URLs only).
4. **Messaging (CDS):**
   - EUM SMS/RCS: create in CDK (`aws_cdk.aws_enduser_messaging` / via the service API),
     config (sandbox number, sender attributes), and the inbound **SMS origination webhook
     URL** pointing at API Gateway.
   - EUM Social WhatsApp: create the connection + phone; wire inbound webhook (security:
     signature verification) to the same API Gateway.
   - SES: `ses.EmailIdentity` (verified domain or sandbox email), SDK outbound allowed.
5. **API Gateway:** REST or HTTP API with secure routes:
   - `POST /webhooks/sms`, `POST /webhooks/whatsapp`, `POST /webhooks/ses`
   - Optional `GET /healthz` per Lambda.
   - Auth: SMS origin signature validation (validate the webhook tokens per channel),
     WhatsApp verification token handshake.
6. **Compute:** Lambda per handler (SMS, WhatsApp, SES, orchestrator-invoker, finance
   scheduler) — with SQS DLQ + `maxRetries` + idempotency keys. Set memory/timeout
   deliberately (Bedrock calls need a few seconds; keep handlers fast, offload agent
   calls to async where possible).
7. **AgentCore (Bedrock):** provision the AgentCore agent definition + the four sub-agents.
   Agents are defined as "agent spec" files (JSON) in `backend/agents/`, deployed via CDK /
   the Bedrock API so the demo can show the *reasoning trace* on screen.
8. **Observability:** every Lambda logs structured JSON; instrument with X-Ray; CloudWatch
   dashboards (traffic per channel, agent latencies, loan status, SES open/click). Add SES
   bounce complaint notifications → topic → Lambda (reputation hygiene).
9. **Budget alarm** resource in CDK with SNS notifications.

**Gate:** `cdk deploy` runs green in a throwaway account IAM context; `GET /healthz` returns
`{"ok":true}`; a test SMS to the sandbox number appears in DynamoDB.

---

## 4. Shared Backend — Session & Domain State (Weeks 1–2)

**Goal:** one source of truth that makes cross-channel continuity real.

1. `backend/shared/session.ts` — `SessionStore` class over DynamoDB:
   - `upsert`, `get`, `appendMessage`, `closeSession`, `touch(lastActiveAt)`.
   - Idempotent message insertion (`dedupeKey = channel + msgId`) so re-delivered webhooks
     can't corrupt state.
2. `backend/shared/types.ts` — domain models: `Farmer`, `Session`, `Message`, `Diagnosis`,
   `Product`, `Dealer`, `Quote`, `LoanAgreement`, `Order`. All validated with Zod at the
   boundary (one schema file shared by all handlers and agents).
3. `backend/shared/context.ts` — a `SessionContext` that threads `sessionId`, `conversation
   summary`, `preferredChannel`, and `channelCapabilities` through every agent call.
4. `backend/shared/keys.ts` — canonical resource names/ARNs (table, bucket, keys) exported
   from CDK output into config.
5. Unit tests for the session store (idempotency, channel migration, TTL cleanup with
   `ttlAttribute`).

**Gate:** a unit-simulated Journey A (SMS→WhatsApp→RCS→SES) mutates one session record
correctly across all four channels.

---

## 5. Channel Layer (Weeks 1–3)

**Goal:** each channel is a thin adapter — parse inbound → normalize → push to orchestrator
queue → translate agent reply → send outbound. No business logic lives here.

Spike order:
1. **`sms_rcs_handler` Lambda:**
   - Inbound: validate webhook (E2EE token), normalize to `Message`, enqueue to orchestrator.
   - Outbound: EUM SMS send; `ChannelCapabilities = { text: true, buttons: false, media: false }`.
   - RCS: rich message with buttons/carousel for purchase cards when `preferredChannel` = RCS;
     `ChannelCapabilities = { text: true, buttons: true, media: false }`.
2. **`whatsapp_handler` Lambda:**
   - Inbound: EUM Social webhook (signature verify), accept `image` message type → store media
     to S3 `photos/` via signed upload or direct link → attach URL to message.
   - Outbound: text or media messages; `ChannelCapabilities = { text: true, media: true }`.
3. **`email_handler` Lambda:**
   - SES send with templates: receipt, loan agreement, check-in reminder. Generate the PDFs
     server-side (e.g. `pdf-lib` / `puppeteer-lambda`) into S3 `pdfs/`, attach, log engagement.
   - Per-channel status callbacks → update session (open/reply/bounce).
4. **Channel escalator (in orchestrator, but built/tested here):** rule that picks the
   best channel for the *next turn* from `channelCapabilities` (diagnosis media → WhatsApp,
   commerce decision → RCS, legal/finance record → SES).

**Gate:** a live SMS to the sandbox number flows `inbound → DynamoDB → test agent reply →
outbound SMS` on a real phone, and a WhatsApp photo upload lands in S3 with a downloadable
Signed URL.

---

## 6. Agent Layer — Bedrock AgentCore Orchestration (Weeks 2–4)

**Goal:** the orchestrator is the company brain; sub-agents are specialists with their own
tools, all addressable through AgentCore so the judge sees real traces.

1. **Orchestrator agent:** intent classification (diagnosis / commerce / finance / logistics /
   chitchat), session continuity (`SessionContext` is injected every turn), channel choice,
   and handoff. Failure policy: unknown intent → handoff to human/partner dashboard, never a
   silent drop.
2. **Diagnosis Agent:** Bedrock vision model on the S3 photo → crop health assessment →
   plain-language explanation in Yoruba/English (locale-aware), question clarification when
   evidence is ambiguous. Tool: `lookupDiagnoses` from a curated knowledge base.
3. **Commerce Agent:** `searchDealers(stock, geo)` against the seeded dealer/stock dataset
   (OpenSearch optional for MVP — in-memory index is fine), build an RCS rich card payload:
   product, price, dealer, distance, "Reserve" button. Tool: `createReservation`.
4. **Finance Agent:** rule-based BNPL eligibility (MVP: conversation signals + basic KYC),
   payment plans via **Paystack** (payment page / split-payment link), generate loan agreement,
   schedule reminders. Tool: `createPaymentPlan`, `issueAgreement`.
5. **Logistics Agent (thin for MVP):** pickup window + confirmation message; can be stubbed
   behind a graceful reply.
6. **Trace visibility:** the orchestrator logs its step trace to CloudWatch AND to the session
   (so the dashboard can render "why this decision" — this is the anti-"scripted" evidence the
   rubric wants).

**Gate:** Journey A runs end-to-end via a test harness (simulated channel adapters) with a
visible AgentCore trace; Journeys B and C produce correct artifacts (plan + agreement,
dashboard events).

---

## 7. Commerce, Finance & the Seed Data (Week 3)

1. `backend/data/dealers.json` — 15–25 realistic dealers across 3 states (Lagos, Oyo, Kano),
   with stock: seed/input categories, prices in NGN, lat/lng, pickup windows.
2. Reservation flow: `createReservation` writes to DynamoDB `Order` (status lifecycle:
   `quote → reserved → confirmed/picked-up`), idempotent, with expiry TTL.
3. BNPL: Paystack **test** mode — produce a split-payment plan; generate `LoanAgreement`
   (PDF) via SES template; reminders scheduled via CloudWatch Events → Lambda (14-day
   check-in + due-date reminders).
4. KYC-lite for MVP: name/phone/state only — no credit bureau. Document the fake-data
   boundaries in the PRD/arch so judges know exactly what is demo vs. real.

**Gate:** a seeded dealer search returns a valid RCS card; a Paystack payment-page
(webhook → `payment.status=success`) flips an order to `confirmed`; an agreement PDF is
retrievable from S3.

---

## 8. Frontend — Landing + Partner Dashboard (Weeks 3–4)

**Goal:** "$10B SaaS, not an AI demo." Typography-led, real data, Linear/Stripe-grade calm.

Two separate Next.js 14 + TS + Tailwind apps as the PDF requires:

1. **`frontend/landing`:**
   - Hero with a **real product screen** (live dashboard conversation feed or a real RCS card
     rendered in a phone frame) — never generic AI art.
   - Serif/grotesque display font, near-black ink, one accent (deep agricultural green / ochre).
   - Sections: problem → how it works (3 journeys) → architecture → partners/NGO CTA → footer.
   - Deployable as static export (fast, cheap); AWS Amplify Hosting or Vercel.
2. **`frontend/dashboard`:**
   - Auth via **Cognito** (staff logins).
   - Data from a new read-only API (API Gateway + DynamoDB queries): live conversation feed,
     diagnosis category breakdown, dealer/stock list, loan health widget, per-region impact.
   - Design: dense calm data tables, quiet borders, one primary action per screen; restrained
     motion used only to show a message hopping channels in the feed.
   - Role: partner/NGO admin + demo mode (a seed "story" the judge can click through in 10s).
3. Both apps share a small `packages/ui` (design tokens, table, cards) to avoid drift.

**Gate:** dashboard renders live (not mocked) data backed by DynamoDB; lighthouse ≥ 90 on
both apps; the landing hero shows a real HarvestOS screen.

---

## 9. Qualification, Security & Scale Hardening (Week 4 — continuous)

Applied throughout, certified here:

1. **Idempotency:** webhooks, reservations, payment callbacks (dedupe keys everywhere).
2. **Security:**
   - Webhook signature verification on all channels (SMS token, WhatsApp verify token,
     SES/SNS topic subscription).
   - KMS at rest everywhere; HTTPS everywhere; no secrets in code or logs (`redact` helper).
   - IAM least privilege; no `*` grants; separate roles per function.
   - Rate limiting on API Gateway + throttling on Lambda.
3. **Failure handling:** DLQs + dead-letter reprocessing; retries with exponential backoff on
   CDS send; graceful degradation (agent down → queue + "we'll text you back").
4. **Observability:** structured JSON logs with `sessionId`/`channel`/`agentId`; CloudWatch
   dashboard; SES bounce handling; X-Ray traces on the agent path. Error tracking via
   **Sentry** on the FastAPI backend (setup steps below).

   ### 4a. Sentry SDK — install & initialize (FastAPI backend)

   **Step 1 — Install the SDK**

   ```bash
   pip install "sentry-sdk" "fastapi"
   ```

   Add `sentry-sdk` (and `fastapi` if not already pinned) to your backend's `requirements.txt`
   / `pyproject.toml` so the container/environment installs them reproducibly.

   **Step 2 — Environment variable**

   Your `.env` already carries `SENTRY_DSN`. Keep the value **out of any source-controlled
   file** — it is a secret. Load it into the app process only at runtime:

   ```bash
   # .env (git-ignored — the ONLY place this lives locally)
   SENTRY_DSN=https://<key>@<org>.ingest.us.sentry.io/<project>
   ```

   For local dev, a simple loader reads it before anything else (e.g. `python-dotenv` in
   `main.py`, or your CDK-provided Lambda/ECS env mapping in staging/prod). The DSN must be
   present **before** `sentry_sdk.init()` runs, or Sentry silently no-ops.

   **Step 3 — Initialize in `main.py`**

   Call `sentry_sdk.init()` at the very top of the application (before `FastAPI()` is
   constructed) so every request is captured:

   ```python
   import sentry_sdk
   from sentry_sdk.integrations.fastapi import FastApiIntegration
   from sentry_sdk.integrations.starlette import StarletteIntegration

   sentry_sdk.init(
       dsn=os.getenv("SENTRY_DSN"),
       enable_tracing=True,                 # required for the two sample rates below
       traces_sample_rate=1.0,              # 100% of transactions traced (lower to 0.x in prod)
       profiles_sample_rate=1.0,            # enables profiling; capture like traces
       integrations=[
           FastApiIntegration(transaction_style="endpoint"),
           StarletteIntegration(transaction_style="endpoint"),
       ],
       send_default_pii=False,              # farmers' phone numbers must never leak to Sentry
   )

   from fastapi import FastAPI

   app = FastAPI(title="HarvestOS API")
   ```

   **Step 4 — Sanitize PII before shipping.** Callers' phone numbers and conversation text
   are PII. Before going live, add a `before_send` hook that strips body fields
   (`text`, `mediaUrl`, `phoneNumber`) from every envelope, so error traces can't leak
   farmer data:

   ```python
   SENSITIVE_KEYS = {"text", "mediaurl", "phonenumber", "body", "message"}

   def before_send(event, hint):
       def scrub(obj):
           if isinstance(obj, dict):
               return {k: ("[redacted]" if k.lower() in SENSITIVE_KEYS else scrub(v))
                       for k, v in obj.items()}
           if isinstance(obj, list):
               return [scrub(v) for v in obj]
           return obj
       return scrub(event)

   sentry_sdk.init(..., before_send=before_send)
   ```

   **Step 5 — Verify (dev).** Trigger an error (raise inside a route, or call
   `sentry_sdk.capture_message("HarvestOS boot check")`) and confirm the event appears under
   Issues → FastAPI in your Sentry project, with `sessionId`/`channel`/`agentId` as
   tags/custom context set via `sentry_sdk.set_tag(...)` in the channel handlers.

   **Gate:** a deployed fatal error (or a forced raise in a smoke test) produces a Sentry
   issue with full stack trace, transaction name, and **no** farmer PII.
5. **Cost guardrails:** CloudWatch budget alarm; Bedrock token budget per session; CDS send
   budget. Add a `dryRun` mode so demo days can't accidentally bill.

**Gate:** a security checklist pass (OAuth/secret scan, webhook spoof test, IAM review) is
green; a chaos test (kill Bedrock temporarily) degrades gracefully.

---

## 10. Testing — the Three Journeys as Automated Proof (Week 4)

1. **Unit:** session store, channel normalizers, intent router, finance rules, RCS card
   builder.
2. **Integration (simulated channels):** a harness drives Journey A/B/C through the real
   orchestrator + agents with stub CDS senders, asserting artifacts (photo → diagnosis →
   RCS card → reservation → agreement → receipt → reminder).
3. **Negative tests:** wrong/absent webhook signatures rejected; replayed webhooks don't
   double-reserve; unpayrolled dealer (no stock) path gives a clean fallback.
4. **Live smoke:** real phone Journey A with the curated photo set only (never improvise an
   unseen photo live — PRD §14).

**Gate:** `npm test` green in CI; a recorded live-run video passes the demo-script beats.

---

## 11. Demo Package (Week 5)

1. `docs/architecture.png` — redraw the PDF diagram cleanly (asset shown on video at 2:10–2:25).
2. `docs/demo-script.md` — the 3-minute script from PRD §13, time-stamped.
3. Record: real phone on screen 0:20–1:40 (SMS→WhatsApp→RCS→receipt), cut to live dashboard
   1:40–2:10, architecture 2:10–2:40, ACE/GTM close 2:40–3:00. Show at least one AgentCore
   trace on screen to prove it's agentic.
4. If entering Meta's "$10K Best of WhatsApp" track: write the WhatsApp usage write-up.

**Gate:** video under 3:05, renders at 1080p, every claim visible on screen is real.

---

## 12. Launch & Submission Checklist

- [ ] Repo public (OSS license in About) **or** private + shared with `testing@devpost.com`
      and `aws-cds-partner@amazon.com`.
- [ ] Architecture diagram + text description committed.
- [ ] 3-minute demo video uploaded.
- [ ] URL to deployed project (or run instructions that work on a fresh machine).
- [ ] AWS Partner Central **ACE opportunity** created with campaign
      `AWS CDS Agentic AI Hackathon -Sept. 2026`.
- [ ] Secrets rotated once more before making the repo public; `.env` never in history (use
      `git filter-repo` + rotate again if it ever leaked).
- [ ] Cost ceiling hit your alert? Check before submission; confirm no surprise spend.

---

## 13. Week-by-Week Map (from PDF §11, now with infra detail)

| Window | Focus | Key deliverable present |
|---|---|---|
| Week 1 | CDK skeleton; SMS+WhatsApp webhooks; DynamoDB schema; orchestrator→stub diagnosis | Green `cdk deploy` + live inbound SMS in DB |
| Week 2 | Vision diagnosis on real photos; seeded dealer/stock; RCS rich cards end-to-end | Journey A on real phone |
| Week 3 | Finance (rule-based BNPL via Paystack); SES receipts/agreements; reminders; landing | Payment-webhook → order confirmed |
| Week 4 | Partner dashboard, live feeds/impacts; polish; automated journey tests | Dashboard live + tests green |
| Week 5 | Demo video, architecture.png, ACE opportunity, submit | Submission checklist done |

---

## 14. Definition of "World-Class" (the bar this plan holds)

- A stranger can stand up the entire platform in < 30 minutes with two commands.
- Every demo claim is a real system, not a mock: real phone, real channels, real DB writes.
- The agentic handoff is **provable** (traces on screen), not claimed.
- Code is typed, tested, linted, and reviewed; infra is immutable and re-deployable.
- The product story closes a real commercial loop (advisory → inputs → finance → fulfillment),
  not a Q&A bot.
- Security is take-it-for-granted: no leaked keys, least privilege, signed webhooks,
  encrypted-at-rest, budget alarm that actually fires.