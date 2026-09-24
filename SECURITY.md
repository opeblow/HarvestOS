# Security policy

## Supported versions

Security fixes are made against the current `main` branch. No release support window has been established yet.

## Report a vulnerability

Please do not open a public issue for a suspected vulnerability. Use GitHub's **Report a vulnerability** flow in the repository Security tab, or contact the repository maintainers privately. Include affected paths or endpoints, impact, and safe reproduction details. Do not include real farmer data or credentials.

We will acknowledge reports as soon as practical, investigate, and coordinate a fix and disclosure with the reporter. Please allow maintainers time to address the issue before public disclosure.

## Security expectations

- Treat any credential committed or shared outside its secret store as compromised: revoke and rotate it promptly.
- Keep `.env` local and use `.env.example` only for variable names and safe placeholders.
- Configure production CORS to an explicit allowlist; do not expose partner data without authentication and tenant authorization.
- Verify channel webhook signatures and payment provider callbacks before enabling live traffic.
- Use least-privilege cloud roles, encrypted storage, private object access, rate limits, and PII-safe logs.
- The console's signed session protects a single configured partner account, but it is not a multi-tenant identity system. The development backend deliberately bypasses API bearer checks; deployed environments must use `APP_ENV=prod`, HTTPS, and the shared signing secret. Seeded data is not a verified inventory feed.
