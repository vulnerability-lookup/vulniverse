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

`config/vulniverse.toml` controls which built-in panels/modules the
standalone app shows.

  ```bash
  cp config/vulniverse.toml.sample config/vulniverse.toml
  ```

- **Fallback**: if `vulniverse.toml` doesn't exist, the backend falls back
  to reading `vulniverse.toml.sample` directly, so a fresh checkout with no
  real config file behaves exactly like the sample's own values — nothing
  here is required to get started.

### `[panels]` / `[modules]`


```toml
[panels]
"templates"    = true
"stats"        = true
"vl"           = true
"cve-program"  = true
"gcve-identifier" = false

[modules]
"download-json" = true
```

CNA-publication credentials — "Vulnerability-Lookup" (target id `vl`) and
"CVE Program" (target id `cve-program`) — are **not** configured here.
Each registered user sets their own under their account's CNA credentials
page; they're stored per-user, encrypted at rest. See [Running in
production](production.md).

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

