---
icon: lucide/home
---

# Vulniverse

Vulniverse is a web-based editor for authoring, reviewing, validating, and
storing vulnerability records in the [CVE Record
Format](https://cveproject.github.io/cve-schema/) 5.2.0,
[GCVE BCP-05](https://gcve.eu/bcp/gcve-bcp-05/) 1.7 and
[OSV](https://ossf.github.io/osv-schema/) 1.9.2. It is intended as a
modern replacement for [Vulnogram](https://github.com/Vulnogram/Vulnogram),
with integration as a first-class goal: use it as a complete standalone
application, embed the editor in
[Vulnerability-Lookup](https://github.com/vulnerability-lookup/vulnerability-lookup),
or connect it to any software that works with these formats.

## Choose your path

<div class="grid cards" markdown>

-   **Just me**

    ---

    Run Vulniverse for yourself on your own machine: a few commands with
    Docker, no accounts, records stored locally.

    [Single-user quick start](quickstart/single-user.md)

-   **My team**

    ---

    Set up a shared server with accounts, organisations, two-factor
    authentication and publishing to Vulnerability-Lookup.

    [Team server quick start](quickstart/team.md)

-   **Embed it**

    ---

    Put the editor into your own application as a single Web Component,
    with your own storage behind it.

    [Embedding quick start](quickstart/embed.md)

-   **Using the editor**

    ---

    A short tour of the forms, the record tree, change tracking,
    templates, Patch2Vuln and publishing.

    [Using the editor](guide/editor.md)

</div>

## How it fits together

Vulniverse is a Vue 3 frontend and a Flask backend that can be run together
as one application, or used separately:

- **`frontend/`** is the editor UI. It builds two ways: as a standalone
  single-page application, and as a self-contained
  `<vulniverse-editor>` Web Component that any other application can embed.
- **`backend/`** is a Flask JSON API that stores records in a database
  (SQLite by default, PostgreSQL via `DATABASE_URL`) and validates them
  against the bundled schemas. It runs in local mode or in multi-user mode
  with accounts, organisations, roles and optional two-factor
  authentication, and also handles templates, Patch2Vuln jobs and CNA
  publication to Vulnerability-Lookup or the CVE Program. The standalone
  frontend uses it; an embedded editor does not have to.

See [Architecture](development/architecture.md) for how the two talk to
each other, and [Embedding: Vulnerability-Lookup](embedding/vl.md) for a
concrete example of embedding the editor into a host application that uses
its own backend instead.

## Deployment

- [Configuration](setup/config.md): deployment mode, panels, actions,
  features and the backend environment.
- [Docker](setup/docker.md): the container setup for development and
  production.
- [Running in production](setup/production.md): deploying without Docker,
  with gunicorn and systemd.

## Embedding

- [The `<vulniverse-editor>` element](embedding/element.md): the Web
  Component's full API.
- [Embedding: Vulnerability-Lookup](embedding/vl.md): how
  Vulnerability-Lookup wires the editor in.

## Development

- [Build from source](development/from-source.md),
  [Architecture](development/architecture.md) and
  [Manage schemas](development/schema.md): for working on Vulniverse
  itself.
