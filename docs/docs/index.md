---
icon:
---

# Vulniverse

Vulniverse is a web-based editor for authoring, reviewing, validating, and
storing vulnerability records in the [CVE Record
Format](https://cveproject.github.io/cve-schema/). It is intended as a
modern replacement for [Vulnogram](https://github.com/Vulnogram/Vulnogram),
with integration as a first-class goal: use it as a complete standalone
application, embed the editor in
[Vulnerability-Lookup](https://github.com/vulnerability-lookup/vulnerability-lookup),
or connect it to any software that works with the CVE Record Format.

The project targets **CVE Record Format 5.2.0**, and also supports
authoring and validating the **GCVE BCP-05 1.7** extension profile: a
dedicated `x_gcve` editor, profile-aware schema validation (including the
BCP-05 semantic rules — relationships required for certain record types,
`language` required for translations, relationship-type checking), and a
"Create as GCVE" option alongside "Create as CVE" when starting a new
record in the standalone app.

!!! note

    Vulniverse is under active development. The editor and API are usable,
    but interfaces and deployment instructions may change before the first
    stable release.

## Two independent halves

Vulniverse is a Vue 3 frontend and a Flask backend that can be run together
as one application, or used separately:

- **`frontend/`** is the editor UI. It builds two ways: as a standalone
  single-page application, and as a self-contained
  `<vulniverse-editor>` Web Component that any other application can embed.
- **`backend/`** is a small Flask JSON API that stores records in SQLite and
  validates them against the bundled CVE schema. The standalone frontend
  uses it; an embedded editor does not have to.

See [Architecture](development/architecture.md) for how the two talk to
each other, and [Embedding: Vulnerability-Lookup](embedding/vl.md) for a
concrete example of embedding the editor into a host application that uses
its own backend instead.

## Where to go next

- [Get started](setup/setup.md) — install the prerequisites and run the
  standalone application locally.
- [Configuration](setup/config.md) — the handful of things that are
  actually configurable today.
- [Manage schemas](setup/schema.md) — updating to a new upstream CVE or
  GCVE schema version.
- [Architecture](development/architecture.md) — how the frontend and
  backend are structured, and how the editor stays embeddable.
- [Embedding: Vulnerability-Lookup](embedding/vl.md) — how the
  `<vulniverse-editor>` component is wired into Vulnerability-Lookup.
