# HarvestOS architecture

## System boundaries

```text
External channels (optional adapters)
  └─ channel adapters (routers/webhooks.py, channels/)
      └─ normalized Message
          └─ journey service
              ├─ orchestrator and specialist agents
              ├─ session store (memory or DynamoDB)
              └─ notification service
                  ├─ in-app inbox (always)
                  └─ enabled external providers (optional)

Partner browser ── dashboard API (routers/dashboard.py) ── session store + inbox + dealer seed
CDK app ── storage / compute / observability resources (SES + S3 optional)
```

Channel adapters translate provider payloads into the shared message model. The notification service always persists every user-facing update to the in-app inbox and only attempts external delivery through providers that are explicitly enabled. Agent modules route intent and update journey state. The session store is the local system of record for conversation continuity. Dashboard endpoints aggregate that state and mask phone numbers before returning rows.

## Optional adapters and the core

The product must run with no external messaging or object storage. Core delivery is the in-app inbox (`NOTIFICATION_PROVIDER=in_app`), and the external providers `EMAIL_PROVIDER`, `SMS_PROVIDER`, and `WHATSAPP_PROVIDER` default to `disabled`; `ASSET_STORAGE` defaults to `local`. `validate_settings()` enforces this at startup:

- Core settings (`STORAGE`, `NOTIFICATION_PROVIDER`) are always validated.
- Optional providers are validated only when enabled. `EMAIL_PROVIDER=ses` requires `SES_FROM_ADDRESS`, `SMS_PROVIDER=eum` requires `SMS_ORIGINATION_IDENTITY`, `WHATSAPP_PROVIDER=eum` requires `WHATSAPP_PHONE_NUMBER_ID`, and `ASSET_STORAGE=s3` requires `ASSET_BUCKET`.
- A disabled channel resolves to a `DisabledAdapter`/`DisabledNotificationProvider` that raises a clear `ProviderError` if used directly, so a disabled channel is never mistaken for a delivered message.

## Data flow and ownership

- **Identity:** phone number joins local channel turns to a session. Production should use a keyed, tenant-aware identity mapping rather than exposing raw numbers as database keys.
- **Conversation:** inbound/outbound turns, channel history, journey stage, diagnosis, quote, reservation, and loan plan live on the session.
- **Notifications:** the in-app inbox is the durable record of every update, with category, entity references, and an optional external-delivery flag. Dashboard endpoints expose and mark these read.
- **Dealer data:** `backend/app/data/dealers.json` provides repeatable sample supply. Treat it as seed data, not a verified live inventory feed.
- **Media/documents:** local asset storage is the default (`ASSET_LOCAL_DIR`, git-ignored). When S3 is enabled, an encrypted object bucket is used; production media access needs private objects, bounded signed URLs, retention policy, and malware/content validation.
- **Dashboard:** read-only endpoints expose aggregate totals, masked conversation rows, and the notification inbox. The Next.js console protects UI and proxy routes with a signed single-partner session; FastAPI validates the same token in deployed mode. Tenant scoping, backend pagination, and audit events remain necessary before multi-partner deployment.

## Runtime modes

| Mode | Persistence | Agents | Outbound messages | Use |
| --- | --- | --- | --- | --- |
| Local default | In-memory sessions, local assets | Rule-based | In-app inbox; external channels disabled | Development and scripted demo |
| AWS core | DynamoDB sessions, local assets | Current configured backend | In-app inbox; external channels disabled | Integration work without messaging services |
| AWS with adapters | DynamoDB plus optional S3 | Current configured backend | In-app inbox plus enabled SES/SMS/WhatsApp adapters | Full integration; verify each service and account prerequisite |

The current repository does not yet provision or prove the full PRD topology of Bedrock AgentCore, Cognito, verified CDS channels, or an asynchronous queue with DLQ. The existing CDK stack should be reviewed against account-specific service support and the deployment plan before use.

## Trust boundaries and production requirements

1. **Inbound webhooks:** SMS has a shared query token and WhatsApp has a verification handshake in the current code; inbound WhatsApp POST authenticity and SES notification authenticity are not fully verified. Implement provider signature verification, timestamp/replay limits, and request size limits.
2. **Dashboard:** the browser uses a signed session and server-side data proxy. Configure credentials in a secret store, add TLS, tenant scoping, durable rate limiting, and audited exports before exposing partner data to multiple organizations.
3. **Payments:** keep test credentials in secret storage; authenticate and idempotently process payment callbacks before changing order/loan state.
4. **Reliability:** add a durable queue, idempotency keys, bounded retries, dead-letter handling, and operator replay before relying on channel delivery.
5. **Privacy:** minimize stored message/media content, mask identifiers in telemetry, redact exceptions, set retention/erasure rules, and obtain consent for collection and messaging.
6. **Finance and agronomy:** make terms, provenance, uncertainty, human escalation, and local regulatory review explicit before real use.
7. **Cloud edge and retention:** the CDK foundation currently exposes an HTTP ALB and retains encrypted data resources if the stack is deleted. Add HTTPS with a managed certificate before sending sensitive traffic; plan explicit, authorized data lifecycle and deletion before deployment.

## Scaling path

Keep domain transitions in application services rather than channel handlers. Extract typed ports for session storage, dealer search, payments, and channel delivery; add provider implementations behind those ports. Move webhook work to durable jobs with idempotent consumers. Partition tenant and farmer access explicitly, then add observability around queue age, end-to-end resolution time, channel delivery, agent latency, inventory freshness, and cost per completed journey.
