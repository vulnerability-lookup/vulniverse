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

`config/vulniverse.toml` controls two things: which
built-in panels/modules it shows, and the credentials for the CNA
publication targets ("Vulnerability-Lookup" and "CVE Program" panels). 

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

### `[integrations.<target>]`

Credentials for the CNA-publication panels — "Vulnerability-Lookup"
(target id `vl`) and "CVE Program" (target id `cve-program`). 

```toml
[integrations.vl]
cve_url      = "https://your-vl-instance.example/api/cna"
short_name   = "..."
org_id       = "..."          # this CNA's registered UUID
cve_api_org  = "..."          # CVE-API-ORG auth header value
cve_api_user = "..."
cve_api_key  = "..."
```

## Backend environment (`.env`)

The `backend/.env` file is needed to start the backend:

```bash
cd backend
cp .env.sample .env
```

And a secret key need to be set: 

```bash
python -c "import secrets; print(secrets.token_hex(32))"   # paste into SECRET_KEY=
```

Optionally the DB adress can be changed here as well.


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

