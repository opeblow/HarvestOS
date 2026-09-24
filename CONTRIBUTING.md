# Contributing to HarvestOS

Thanks for helping build tools that connect farmer support to local supply. Issues and pull requests are welcome.

## Before you start

- Read the [README](README.md), [architecture notes](docs/architecture.md), and [Code of Conduct](CODE_OF_CONDUCT.md).
- Open an issue first for large changes so the product scope and design can be aligned.
- Never include real farmer data, credentials, private keys, `.env` files, or unredacted logs in a commit or issue.

## Development setup

Install Node.js 20 or newer and Python 3.11 or newer. Follow the README to install dependencies and start the API and dashboard. The default local runtime uses in-memory state and seeded dealers; external AWS services are optional.

## Change guidelines

- Keep channel adapters thin; put journey decisions in agents/services and shared state in the session store.
- Validate and normalize data at system boundaries. Keep farmer identifiers masked in operational views and logs.
- Keep UI claims tied to data returned by the API. Label seeded or simulated behavior clearly.
- Update documentation and `.env.example` when configuration changes. Never add secrets to examples.
- Keep changes focused and explain the user outcome, implementation, and limitations in the pull request.

## Pull requests

1. Describe the problem and the behavior change.
2. List the checks you ran and any manual verification performed.
3. Include screenshots or a short screen recording for visual changes.
4. Call out configuration, data model, security, or deployment implications.
5. Confirm the contribution is yours to submit and does not include third-party material without permission.

Maintainers review for product fit, correctness, privacy, accessibility, and operational clarity. Passing CI is necessary but does not replace review.
