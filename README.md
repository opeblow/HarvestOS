<p align="center">
  <img src="frontend/landing/app/icon.svg" width="56" height="56" alt="HarvestOS leaf mark" />
</p>

<h1 align="center">HarvestOS</h1>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-yellow.svg" alt="License: MIT" /></a>
  <a href="package.json"><img src="https://img.shields.io/badge/node-%3E%3D20-brightgreen.svg" alt="Node.js 20+" /></a>
  <a href="backend/pyproject.toml"><img src="https://img.shields.io/badge/python-3.11%2B-blue.svg" alt="Python 3.11+" /></a>
  <a href="tsconfig.base.json"><img src="https://img.shields.io/badge/typescript-strict-informational.svg" alt="TypeScript: strict" /></a>
  <a href="infra/cdk"><img src="https://img.shields.io/badge/infrastructure-AWS%20CDK-orange.svg" alt="AWS infrastructure: CDK" /></a>
</p>

**A farmer's text should open a path to a harvest.** HarvestOS connects crop guidance, local agricultural supply, and financing in one continuous conversation across low-bandwidth messaging channels.

Built for the AWS Communication Developer Services (CDS) Agentic AI Partner Hackathon. The repository contains a runnable local journey and an AWS infrastructure foundation. Channel and cloud integrations require account setup; see [what works today](#implementation-status) before presenting a live integration as available.

## Landing page

The public site introduces HarvestOS and the farmer journey, from a first crop question to connected commerce. It explains how SMS, WhatsApp, messaging apps, and email share one continuous session, how local supply and financing are brought into reach, and how cooperatives and NGOs get a partner view of the work. Each section links through to the partner workspace so visitors can follow the story into the product.

![HarvestOS responsive landing page tour](docs/landing-tour.gif)

## Partner sign-in and onboarding

Partner sign-in opens the operations console after authenticating with workspace credentials. The page explains what partners can do once inside: a connected view of the conversations, local supply, and payment plans moving through their farmer network. A successful sign-in issues a signed eight-hour HttpOnly session, so the operator lands directly on the dashboard Overview to begin triaging journeys.

![HarvestOS partner sign-in tour](docs/auth-tour.gif)

## Product tour

The partner overview consolidates live network metrics — farmers reached, messages handled, crop issues assessed, and input orders — alongside real-time conversation activity. A conversations table surfaces each farmer journey and its stage across channels, while the dealer network and impact & finance panels show input supply and financing supported by the connected sessions. Sample data is used throughout the tour.

![HarvestOS partner operations: overview, conversations, and supply network](docs/product-tour.gif)

## The farmer journey

```mermaid
sequenceDiagram
    actor Farmer
    participant Channels as SMS / WhatsApp / RCS / Email
    participant API as FastAPI adapters
    participant Agent as Journey orchestrator
    participant Store as Session store
    participant Partners as Dealer / finance agents
    participant Console as Partner dashboard

    Farmer->>Channels: Describe crop issue
    Channels->>API: Normalize inbound message
    API->>Agent: Continue session
    Agent->>Store: Load and update shared context
    Agent-->>Farmer: Ask for a photo on WhatsApp
    Farmer->>Channels: Send crop photo
    Channels->>API: Attach media to same session
    API->>Agent: Diagnose and source inputs
    Agent->>Partners: Find stock / payment plan
    Partners-->>Agent: Quote and options
    Agent-->>Farmer: Rich purchase choice on RCS
    Agent->>Store: Record reservation and journey state
    Agent-->>Farmer: Send receipt by email
    Console->>API: Read operational aggregates
    API->>Store: Read session records
```

## Architecture

```text
SMS / WhatsApp / RCS / Email
             │ channel adapters
             ▼
   FastAPI webhook + dashboard API
             │
             ▼
 Orchestrator ── Diagnosis / Commerce / Finance / Logistics
             │                    │
             ▼                    ▼
 Session store             Dealer and journey state
 memory locally             DynamoDB / S3 in AWS mode
             │
             ▼
 Next.js partner dashboard
```

The channel layer normalizes inbound messages; the journey/orchestrator owns the next action; agent modules handle specialist decisions; the session store preserves channel continuity; the dashboard reads operational aggregates. Full boundary, trust, and deployment notes are in [docs/architecture.md](docs/architecture.md) and [docs/system-design.md](docs/system-design.md).

## Repository layout

```text
HarvestOS/
├── .github/
│   └── workflows/             # CI (tests + lint) and staging deployment
├── backend/                   # FastAPI services
│   ├── app/
│   │   ├── agents/            # diagnosis, commerce, finance, logistics + orchestrator
│   │   ├── channels/          # SMS/RCS, WhatsApp, email channel adapters
│   │   ├── routers/           # webhook ingestion + dashboard API
│   │   ├── services/          # journey orchestration service
│   │   ├── shared/            # cross-agent types, channel policy, session store
│   │   ├── data/              # seeded dealer network
│   │   ├── auth.py            # dashboard session / bearer auth
│   │   ├── config.py          # environment-driven settings
│   │   └── main.py            # FastAPI entrypoint
│   ├── tests/                 # pytest suite
│   ├── Dockerfile
│   └── pyproject.toml
├── docs/                      # architecture, system design, demo script, tour GIFs
├── frontend/
│   ├── landing/               # public marketing site (Next.js)
│   └── dashboard/             # partner operations console (Next.js)
├── infra/
│   └── cdk/                   # AWS CDK: storage, compute, observability
├── package.json               # npm workspace manifest
├── tsconfig.base.json
├── LICENSE
└── README.md
```

## Implementation status

- **Runnable locally:** FastAPI, rule-based diagnosis/commerce/finance/logistics journey, in-memory session store, seeded dealer network, simulated outbound channel adapters, Next.js landing page, and a password-protected partner dashboard with a same-origin API proxy.
- **AWS foundation:** CDK defines storage, compute, and observability infrastructure. AWS mode includes SDK adapters and DynamoDB session storage, but deployment still requires account-specific configuration and verification.
- **Production auth boundary:** the partner console has a signed eight-hour HttpOnly session and the API verifies that session in deployed mode. This MVP login supports one configured partner account; multi-user identity, organization/tenant management, recovery, and Cognito federation remain future work. Production must use a unique high-entropy session secret shared by dashboard and API, HTTPS, and rate limiting at the edge.
- **Not complete as an end-to-end production integration:** Bedrock AgentCore traces, real channel provisioning/webhook signature verification, multi-tenant Cognito identity, async queue/DLQ workflow, payment provider callback verification, and production dashboard hosting.
- **Demo mode is not production:** seeded dealer inventory and local rule-based decisions are for repeatable development; no loan eligibility or agronomic recommendation here should be treated as regulated financial or authoritative agronomic advice.

## Quick start

Requirements: Node.js 20+, npm, Python 3.11+.

```bash
npm ci
python -m venv backend/.venv
# Windows PowerShell
backend/.venv/Scripts/Activate.ps1
pip install -r backend/requirements-dev.txt
```

Create local configuration (PowerShell):

```powershell
Copy-Item .env.example .env
```

Start the API in one terminal:

```bash
npm run backend:dev
```

Start the partner console in another:

```bash
npm run dashboard:dev
```

Open the public landing page at <http://localhost:3000>. Start the partner console with `npm run dashboard:dev`, then visit <http://localhost:3001/login>. The local demo account is `partner@harvestos.local` / `HarvestDemo!2026`; these development-only defaults are rejected in production. The authenticated dashboard reads through its same-origin proxy to the local API at <http://localhost:8000>.

Try the local SMS journey (use a placeholder phone number):

```bash
curl -X POST "http://localhost:8000/webhooks/sms?auth=change-me-random-string" \
  -H "Content-Type: application/json" \
  -d '{"body":"my maize leaves are turning yellow","from":"+2348012345678"}'
```

The default local channel adapters log simulated replies. A memory session disappears when the API process restarts.

## Commands

| Command | Purpose |
| --- | --- |
| `npm run backend:dev` | Start FastAPI on port 8000 |
| `npm run dashboard:dev` | Start partner console on port 3001 |
| `npm run frontend:dev` | Start marketing site on port 3000 |
| `npm run typecheck` | Type-check the TypeScript workspaces |
| `npm run backend:test` | Run backend tests |
| `npm run infra:test` | Run CDK unit tests |
| `npm run infra:synth` | Synthesize the CDK template |

## Configuration and AWS

`.env.example` documents configuration names. Never commit `.env` or paste credentials into issues, logs, screenshots, or CI output. Configure `HARVESTOS_AUTH_EMAIL`, `HARVESTOS_AUTH_PASSWORD`, and `HARVESTOS_SESSION_SECRET` in the dashboard hosting environment; use the same session secret for the backend. The backend uses `APP_ENV=prod` to require the signed bearer token on dashboard endpoints. In ECS, store the secret as a JSON Secrets Manager value with a `session_secret` key and configure `HARVESTOS_AUTH_SECRET_ARN`; the Next.js host must receive that same value through its secret store. The development fallback is intentionally not used when `NODE_ENV=production`.

Use short-lived credentials locally where possible and GitHub OIDC for deployments. Before AWS deployment, review the [implementation plan](implementation.md), CDK outputs, expected spend, account/region, and the current integration status. `npm run infra:deploy` creates billable cloud resources; it is intentionally not part of the default setup. The current ALB output is HTTP-only and stored data resources are retained on stack deletion, so add TLS before any real traffic and plan data cleanup explicitly. Static hosting for the landing page must set security headers at its CDN because Next static export cannot attach response headers.

The staging workflow is manual and uses GitHub Actions OIDC. Configure the `staging` GitHub environment with `AWS_STAGING_ROLE_ARN` and `AWS_REGION`; restrict the IAM role trust policy to this repository and environment. No production deployment workflow is configured.

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), and [SECURITY.md](SECURITY.md). HarvestOS is MIT licensed; see [LICENSE](LICENSE).

## Hackathon demo beats

1. Farmer asks for help over SMS.
2. The orchestrator continues the session and requests crop evidence via WhatsApp.
3. Diagnosis and dealer matching produce an input quote.
4. The farmer reserves or asks about financing; the journey records the outcome.
5. The partner console shows the same session, its stage, and channel history.

Use a verified test environment and clearly identify simulated steps. See [docs/demo-script.md](docs/demo-script.md) for the timed version.
