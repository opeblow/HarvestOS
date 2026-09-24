# Three-minute demo script

This script distinguishes current local behavior from integrations that require AWS credentials, provisioned numbers, or further implementation. Never claim a simulated adapter is a live channel. The core demo runs entirely on the in-app notification inbox with local asset storage; SMS, WhatsApp, RCS, email, and S3 are optional adapters that are disabled by default.

| Time | Beat | On screen |
| --- | --- | --- |
| 0:00–0:20 | A farmer can describe a crop problem in the channel already on their phone. HarvestOS carries that need through advice and access to inputs. | Problem statement and product name |
| 0:20–0:50 | Send the prepared maize message into the local API. Explain that the reply is recorded in the in-app inbox and that external channels are disabled unless configured. | Farmer message / API trace and inbox entry |
| 0:50–1:20 | Continue the same session through evidence, diagnosis, and a dealer quote. Explain the current rule-based or model-backed path accurately. | Journey response and quote |
| 1:20–1:45 | Reserve or ask about payment options. Show the state transition; identify sample inventory or test payment behavior. | Reservation / plan state |
| 1:45–2:10 | Open the partner console and find the same masked conversation, channel history, and in-app notification inbox. | Dashboard live totals, conversation row, and inbox |
| 2:10–2:40 | Walk through the notification service, optional channel adapters, orchestrator/agents, shared session state, and the dashboard. Name only AWS resources actually running in this environment. | Architecture diagram |
| 2:40–3:00 | Close on the partner buyer: a cooperative or NGO can coordinate trusted advice, local supply, and financing across a farmer network. State what is ready next. | Partner view and next milestone |

For a fully live channel demo, first enable the relevant provider (`EMAIL_PROVIDER`/`SMS_PROVIDER`/`WHATSAPP_PROVIDER`) with its configuration, rehearse on the same provisioned test numbers and curated crop photo, verify each delivery callback, and capture an agent trace before recording.
