---
icon: lucide/users
---

# My team: a shared server

This page is for the admin who sets up one Vulniverse server for a team.
It uses **multi-user mode**: everyone has their own account with
two-factor authentication, and people work together in
**organisations**. Members of an organisation share its records, drafts
included.

The steps use Docker. To run it directly on the host with systemd and
nginx instead, install it with
[Running in production](../setup/production.md), set the config from
steps 4 and 5 below, and run the `flask` commands as
`uv run flask --app vulniverse_api …` in `backend/` instead of
`docker compose exec backend flask --app vulniverse_api …`.

You need a Linux server with Git, Docker with Compose, `python3`, a
domain name pointing to it, and (recommended) PostgreSQL.

## 1. Get the code

```bash
git clone https://github.com/vulnerability-lookup/vulniverse.git
cd vulniverse
cp backend/.env.example backend/.env
```

Run every following command from this directory.

## 2. Generate the two keys

The backend refuses to start without them. Generate a secret key:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Paste the output after `SECRET_KEY=` in `backend/.env`. Then generate
the key that encrypts CNA credentials and 2FA secrets:

```bash
python3 -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```

Paste it after `CNA_CREDENTIAL_ENCRYPTION_KEY=`.

!!! warning

    Back up `backend/.env` somewhere safe. If
    `CNA_CREDENTIAL_ENCRYPTION_KEY` is lost or changed, nobody's CNA
    credentials can be read any more, and every user's 2FA has to be
    reset.

## 3. Point it at PostgreSQL

SQLite works, but for several people writing at once PostgreSQL is the
better choice. Create a role and a database for Vulniverse (see
[Running in production, step 2](../setup/production.md#step-2-optional-set-up-postgresql)),
then set `DATABASE_URL` in `backend/.env`. Use the `postgresql+psycopg://`
scheme; plain `postgresql://` won't work:

```
DATABASE_URL=postgresql+psycopg://vulniverse:your-password@host.docker.internal:5432/vulniverse
```

`host.docker.internal` reaches PostgreSQL on the Docker host. PostgreSQL
must then accept connections from the Docker network, not only from
`localhost` (`listen_addresses` and `pg_hba.conf`). For a database on
another machine, use its host name instead.

## 4. Switch to multi-user mode

```bash
cp config/vulniverse.toml.sample config/vulniverse.toml
```

Edit the `[server]` table in `config/vulniverse.toml`:

```toml
[server]
mode = "multiuser"
registration = "invite"
two_factor = true
```

- `registration` decides who can create an account:
    - `invite`: only people with an invitation link from an organisation.
      Recommended for a team.
    - `open`: anyone who can reach the server.
    - `closed`: nobody. Invitation links then only work for people who
      already have an account.
- `two_factor = true` makes every account set up an authenticator app
  (TOTP) before it can do anything else. Recommended.

Details: [Configuration](../setup/config.md#server).

## 5. Choose your panels and actions

In the same `config/vulniverse.toml`, each panel is a table such as
`[panels.patch2vuln]` with an `enabled` switch; actions are listed under
`[actions]`. They apply to everyone on the server.

| Panel or action | On by default | What it needs |
| --- | --- | --- |
| Templates | yes | nothing |
| Record Quality | yes | nothing |
| Patch2Vuln | yes | a Patch2Vuln service: set `api_url` under `[panels.patch2vuln]`, or turn it off with `enabled = false` |
| Vulnerability-Lookup | no | `enabled = true` and the servers to publish to (step 13) |
| CVE Program | no | `enabled = true` and the CVE Services server |
| Download, Tutorial (actions) | yes | nothing; set to `false` under `[actions]` to hide them |

!!! warning "Patch2Vuln points to a placeholder"

    The sample's `api_url` is `https://patch2vuln.example.org`, which
    doesn't exist. Until you set your own service there (or turn the panel
    off), the panel is shown but every analysis fails.

The `[features]` table switches the CWE, CAPEC and CPE suggestions in the
form; CPE suggestions also need the local catalog, which you fill once
Vulniverse is running with
`docker compose exec backend flask --app vulniverse_api cpe sync`.

The backend reads the file when it starts. Once it's running, restart it
after each change:

```bash
docker compose restart backend
```

Every setting, panel and action: [Configuration](../setup/config.md#panels-actions).

## 6. Start it

```bash
docker compose -f compose.yaml -f compose.prod.yaml up -d --build
```

When the build is done, `docker compose ps` shows a `backend` and a
`frontend` container running. The app answers on
`http://127.0.0.1:8080`, on the server only.

## 7. Set up the database

The containers don't do this on their own:

```bash
docker compose exec backend flask --app vulniverse_api db upgrade
```

Don't run `init-local-user`: that is for local mode only.

## 8. Create the first admin

```bash
docker compose exec backend flask --app vulniverse_api create-admin admin@example.com
```

It asks for a password twice and prints
`Created the admin account admin@example.com.` This account is an
**instance admin**: it manages all users and organisations.

## 9. Put TLS in front of it

Vulniverse doesn't handle HTTPS itself. Run a reverse proxy on the host
that terminates TLS and forwards to `127.0.0.1:8080`. With
[Caddy](https://caddyserver.com/), which fetches a certificate on its
own, the whole site config is:

```
vulniverse.example.org {
    reverse_proxy 127.0.0.1:8080
}
```

With nginx, use `proxy_pass http://127.0.0.1:8080;` and add a
certificate, for example with Certbot. Then open
`https://vulniverse.example.org`.

## 10. Log in and set up 2FA

Log in with the admin account. With `two_factor = true`, Vulniverse
shows a QR code: scan it with an authenticator app (Aegis, Google
Authenticator, 1Password, …) and enter the code it shows. From now on
every login asks for a code after the password.

## 11. Create an organisation

Records always belong to an organisation, so create one before anyone
starts writing.

1. Open **Admin → Organisations** in the top bar.
2. Enter a name, for example your CNA's, and click **Create**.
3. Select the new organisation, pick your own account under
   **Add an existing account…**, choose the role **Admin** and click
   **Add**. Now you can create records and invite people to it.

## 12. Invite your team

1. Open **Members** in the top bar.
2. Under **Invitation links**, choose the role (**Editor** or **Admin**)
   and click **Create link**.
3. Send the link to one person. They open it, register (or log in if
   they already have an account) and join the organisation.

Each link works once, for seven days, and can be revoked on the same
page. Organisation admins can invite people themselves; editors work on
records. Instance admins can also add an existing account to any
organisation from **Admin → Organisations**.

## 13. Connect to Vulnerability-Lookup (optional)

To reserve and publish GCVE IDs on a
[Vulnerability-Lookup](https://github.com/vulnerability-lookup/vulnerability-lookup)
instance, two things are needed.

**You, the operator**, list the servers users may publish to in
`config/vulniverse.toml`. Vulniverse only ever contacts listed servers:

```toml
[panels.vl]
enabled = true

[[panels.vl.instances]]
id = "circl"
name = "CIRCL Vulnerability-Lookup"
api_url = "https://vulnerability.circl.lu/api/cna"
```

Restart the backend to apply it:

```bash
docker compose restart backend
```

**Each user** then opens **CNA credentials** from their account menu
(`/cna-credentials`), picks the server under **Vulnerability-Lookup**,
enters their API key, and optionally a short name and Org ID, then
clicks **Save**. Credentials are stored per user, encrypted with
`CNA_CREDENTIAL_ENCRYPTION_KEY`.

Details: [Configuration](../setup/config.md#panels-actions).

## When someone is locked out

- **Lost authenticator device**: an instance admin opens
  **Admin → Users** and clicks **Reset 2FA** for that user. They set it
  up again at their next login.
- **Forgotten password**: on the same page, **Reset password** shows a
  new random password once; pass it on to the user.
- **The only admin lost their device**: reset it from the server:

    ```bash
    docker compose exec backend flask --app vulniverse_api reset-two-factor admin@example.com
    ```

## Updating

```bash
git pull
docker compose -f compose.yaml -f compose.prod.yaml up -d --build
docker compose exec backend flask --app vulniverse_api db upgrade
```

Run `db upgrade` after every update: the containers don't migrate the
database by themselves. Back up the database first (for PostgreSQL, with
`pg_dump`).

## Next steps

- [Configuration](../setup/config.md): every setting in
  `config/vulniverse.toml`, including panels such as Patch2Vuln.
- [Running in production](../setup/production.md): the same deployment
  without Docker, with systemd and nginx.
- [Using the editor](../guide/editor.md): send this to your team.
