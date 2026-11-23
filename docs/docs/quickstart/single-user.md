---
icon: lucide/user
---

# Just me: a single-user instance

This page gets Vulniverse running on your own machine in about five
minutes. It uses **local mode**: no accounts, no login. Everyone who can
reach the page works as one built-in user, so keep it on `localhost`.

You need Git, Docker with Compose, and `python3` (only to generate two
keys).

## 1. Get the code

```bash
git clone https://github.com/vulnerability-lookup/vulniverse.git
cd vulniverse
```

Run every following command from this directory.

## 2. Create the environment file

```bash
cp backend/.env.example backend/.env
```

## 3. Generate the two keys

The backend refuses to start without them. Generate a secret key:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Paste the output after `SECRET_KEY=` in `backend/.env`. Then generate
the key that encrypts stored CNA credentials:

```bash
python3 -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```

Paste it after `CNA_CREDENTIAL_ENCRYPTION_KEY=`.

!!! warning

    Keep a copy of `backend/.env`. If you lose or change
    `CNA_CREDENTIAL_ENCRYPTION_KEY`, any saved CNA credentials can no
    longer be read.

Leave `DATABASE_URL` unset: Vulniverse then uses a SQLite file.

## 4. Choose your panels and actions

Settings live in `config/vulniverse.toml`. Without it, Vulniverse uses
the defaults from `config/vulniverse.toml.sample`: local mode (no login)
and the panels below. To change anything, copy the sample and edit the
copy:

```bash
cp config/vulniverse.toml.sample config/vulniverse.toml
```

Each panel is a table such as `[panels.patch2vuln]` with an `enabled`
switch; actions are listed under `[actions]`.

| Panel or action | On by default | What it needs |
| --- | --- | --- |
| Templates | yes | nothing |
| Record Quality | yes | nothing |
| Patch2Vuln | yes | a Patch2Vuln service: set `api_url` under `[panels.patch2vuln]`, or turn it off with `enabled = false` |
| Vulnerability-Lookup | no | `enabled = true` and the servers to publish to (see [My team, step 13](team.md#13-connect-to-vulnerability-lookup-optional)) |
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

You can also skip this step now and come back to it later.

## 5. Start it

```bash
docker compose -f compose.yaml -f compose.prod.yaml up -d --build
```

The first build takes a few minutes. When it is done,
`docker compose ps` shows a `backend` and a `frontend` container running.

## 6. Set up the database

The containers don't do this on their own. Run both commands once:

```bash
docker compose exec backend flask --app vulniverse_api db upgrade
docker compose exec backend flask --app vulniverse_api init-local-user
```

The second one prints `Local user initialized: …`. Without it, every
page shows "Authentication required".

## 7. Open the editor

Open <http://localhost:8080>. You land on the **Records** page.

## 8. Create your first record

1. Click **Create new record**.
2. Pick a format and click its button: **Create as CVE**,
   **Create as GCVE** or **Create as OSV**.
3. The editor opens. Fill in the fields.

## Where your data lives

The database is the file `vulniverse.sqlite` in a Docker volume named
after the directory, usually `vulniverse_backend_instance`. It survives
`docker compose down` and rebuilds. Only `docker compose down -v` deletes
it.

To back it up, make a consistent copy inside the container, then copy it
out:

```bash
docker compose exec backend python -c "import sqlite3; sqlite3.connect('/app/backend/src/instance/vulniverse.sqlite').backup(sqlite3.connect('/app/backend/src/instance/backup.sqlite'))"
docker compose cp backend:/app/backend/src/instance/backup.sqlite ./vulniverse-backup.sqlite
```

Keep `backend/.env` with the backup.

## Updating

```bash
git pull
docker compose -f compose.yaml -f compose.prod.yaml up -d --build
docker compose exec backend flask --app vulniverse_api db upgrade
```

Run `db upgrade` after every update: the containers don't migrate the
database by themselves.

## Next steps

- [Using the editor](../guide/editor.md): a tour of the editor.
- [Configuration](../setup/config.md): turn panels such as Patch2Vuln
  on or off, and the other settings in `config/vulniverse.toml`.
  Restart the backend after a change:
  `docker compose restart backend`.
- [Docker](../setup/docker.md): the Compose files in detail.
- [My team: a shared server](team.md): if you later want real accounts
  for several people.
