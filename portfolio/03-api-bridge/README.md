# API Bridge — Authorized JSON API to CSV

**Client problem:** manual copying of data from an existing JSON API into spreadsheets.

**Deliverable:** reusable command-line exporter with hostname allowlist, HTTPS-only policy, timeout, bounded retries, response-size cap, configurable fields and CSV formula escaping. No third-party packages.

## Run tests (offline, without credentials)

```bash
cd portfolio/03-api-bridge
python -m unittest test_bridge.py -v
```

## Example with a public, authorized API

```bash
python bridge.py --url https://jsonplaceholder.typicode.com/users \
  --host jsonplaceholder.typicode.com --field id --field name --field email \
  --output users.csv
```

The example contacts originate from a public test service, not real client data. Network access is needed for the example only; tests use a fake HTTP transport.

If the authorized API uses a bearer token, set `API_TOKEN` in your shell/environment. Never commit tokens, .env files or exported client data to Git.

**Security and scope:** exact host allowlist, HTTPS, refusal of redirects, limited response size and retries protect against common mistakes, but are **not** a complete SSRF defense or security audit. Use only endpoints and data you are authorized to access. Pagination, rate-limit contracts, schema mapping, production monitoring and OAuth require project-specific engineering.
