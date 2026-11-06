---
icon: lucide/settings
---

# Configuration

This page covers configuring the **standalone app** specifically:
`config/vulniverse.toml` (its own runtime settings) and a short list of
hardcoded backend/frontend-build values. 

How a *host* configures the
embeddable `<vulniverse-editor>` element itself is a separate concern, covered in
[Embedding: The `<vulniverse-editor>` element](../embedding/element.md).

## Config file 

`config/vulniverse.toml` controls the deployment mode, which built-in
panels/actions the standalone app shows, and which suggestion-lookup
features it's allowed to use.

  ```bash
  cp config/vulniverse.toml.sample config/vulniverse.toml
  ```

- **Fallback**: if `vulniverse.toml` doesn't exist, the backend falls back
  to reading `vulniverse.toml.sample` directly, so a fresh checkout with no
  real config file behaves exactly like the sample's own values — nothing
  here is required to get started.

### `[server]`

```toml
[server]
mode = "local" # local or multiuser -> Multiuser is still WIP, do not use in prod
```

`local` (the default) auto-authenticates every request as a single
internal user — there's no login/registration at all. This user has to be
created once, separately from the database migrations:

```bash
uv run flask --app vulniverse_api init-local-user
```

Without it, every request gets "Authentication required" even in local
mode, since `db upgrade` only creates the `user` table, not this row —
see [Get started](setup.md). `multiuser` enables real accounts
(registration/login), but is explicitly still work in progress and isn't
meant for a real deployment yet.

### `[features]`

```toml
[features]
cpeVendors = true
cpeProducts = true
cpeEntries = false
cwe = true
capec = true
```

Which vendor/product/CPE/CWE/CAPEC autocomplete lookups the editor's
repository is allowed to perform. `cpeVendors`/`cpeProducts` are backed by
a local catalog synced via `flask cpe sync` (see
[Architecture](../development/architecture.md)) —
no outbound request at search time either way. `cpeEntries` (full
CPE-identifier suggestions) has no local catalog to serve it from yet, so
it stays disabled regardless of this setting. Disabling a feature here is
enforced on the backend, not just hidden in the UI — the underlying route
returns 404 if a disabled feature is requested directly.

### `[panels]` / `[actions]`

```toml
[panels.stats]
enabled = false

[panels.vl]
enabled = true

[panels.cve-program]
enabled = false

[panels.record-quality]
enabled = true

[panels.patch2vuln]
enabled = true
api_url = "https://patch2vuln.example.org"
# api_token = ""
# models = ["qwen3.8:27b"]
timeout_seconds = 300

[actions]
"download-json" = true
```

A panel id not listed defaults to enabled. Most panels are a plain
`enabled` flag; `[panels.patch2vuln]` additionally carries its own
operational settings (`api_url`/`api_token`/`models`/`timeout_seconds`)
for reaching an external
[Patch2Vuln](https://github.com/gcve-eu/gcve-lab-patch2vuln) web service
instance — see the comments in `config/vulniverse.toml.sample` for the
full set.

As with `[features]`, disabling a panel here is enforced on the backend:
the underlying routes for a disabled panel return 404, not just a hidden
button in the UI.

CNA-publication credentials — "Vulnerability-Lookup" (target id `vl`) and
"CVE Program" (target id `cve-program`) — are **not** configured here.
Each registered user sets their own under the standalone app's own
`/cna-credentials` page; they're stored per-user, encrypted at rest using
`CNA_CREDENTIAL_ENCRYPTION_KEY` (see below).

## Backend environment (`.env`)

The `backend/.env` file is needed to start the backend:

```bash
cd backend
cp .env.example .env
```

A secret key and a CNA-credential encryption key both need to be set:

```bash
python -c "import secrets; print(secrets.token_hex(32))"   # paste into SECRET_KEY=
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"   # paste into CNA_CREDENTIAL_ENCRYPTION_KEY=
```

Optionally the DB address can be changed here as well.


## Frontend dev server

`frontend/vite.config.ts` hardcodes the dev-proxy target:

```ts
server: {
  proxy: {
    "/api": {
      target: "http://127.0.0.1:5000",
      changeOrigin: true,
    },
  },
},
```

If the backend runs on a different host/port during development, this is
the line to change.
