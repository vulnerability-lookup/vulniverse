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
registration = "open" # multi-user mode: open, invite or closed
two_factor = false # multi-user mode: every account must set up 2FA
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

`registration` decides who may create an account in multi-user mode:

- `open` (the default): anyone can register. An invitation link still
  adds the new account to its organisation.
- `invite`: registering needs an organisation's invitation link.
- `closed`: nobody can register. Invitation links still work for
  people who already have an account.

Organisation admins create invitation links on their organisation's
page; a link works once, for seven days, and can be revoked. Any other
value stops the backend from starting.

Create the first instance admin on the server; it asks for a password:

```bash
uv run flask --app vulniverse_api create-admin admin@example.com
```

Email addresses aren't verified, so the command creates the account
itself rather than promoting one somebody registered through the web.
For an address that already has an account, it asks before promoting
it. Until the admin exists, keep `registration` on `invite` or `closed`.

`two_factor = true` makes every account set up two-factor
authentication: after the next login, a user can do nothing else until
they have scanned a QR code with an authenticator app (TOTP, such as
Aegis, Google Authenticator or 1Password) and entered a code from it.
From then on every login asks for a code after the password. After five
wrong codes the code step pauses for 15 minutes. The secrets are
encrypted with `CNA_CREDENTIAL_ENCRYPTION_KEY`; after changing that key,
the stored secrets can't be read, so reset everyone's 2FA (below).

If someone loses their device, an instance admin resets their 2FA
under Admin → Users. If the only admin loses theirs:

```bash
uv run flask --app vulniverse_api reset-two-factor admin@example.com
```

With `two_factor = false` (the default), logins never ask for a code,
even for accounts that set it up earlier.

A password change, a password reset, a 2FA reset and deactivation log
the account out everywhere else, including logins that are waiting for
their code; reactivating an account doesn't bring those sessions back.

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

[[panels.vl.instances]]
id = "circl"
name = "CIRCL Vulnerability-Lookup"
api_url = "https://vulnerability.circl.lu/api/cna"

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
"download" = true
"tutorial" = true
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

The servers the CNA-publication panels — "Vulnerability-Lookup" (target
id `vl`) and "CVE Program" (target id `cve-program`) — may send to are
configured here, as a list per target:

```toml
[[panels.cve-program.instances]]
id = "cve-test"
name = "CVE Program (test)"
api_url = "https://cveawg-test.mitre.org/api"
```

Each entry needs a unique `id`, a `name` shown to users and an http(s)
`api_url`; anything else stops the backend from starting. Without an
entry, publishing to that target isn't possible. Only listed servers are
ever contacted, so users can't make the backend send requests (and their
API keys) anywhere else. If several organisations use different
Vulnerability-Lookup instances, list each of them.

The credentials themselves are **not** configured here. Each registered
user sets their own under the standalone app's `/cna-credentials` page:
which of the listed servers, and their CNA identity and API key. They're
stored per user, encrypted at rest using `CNA_CREDENTIAL_ENCRYPTION_KEY`
(see below). Changing the server requires entering the API key again.

When upgrading, stored credentials whose URL matches a listed server are
assigned to it automatically; the others have to pick a server (and
enter their key again) before publishing works.

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
