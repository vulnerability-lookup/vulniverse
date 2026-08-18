# Vulniverse

Vulniverse is a web-based editor for authoring, reviewing, validating, and
storing vulnerability records. It is intended as a modern replacement for
[Vulnogram](https://github.com/Vulnogram/Vulnogram), with integration as a
first-class goal: use the complete standalone application, embed the editor in
[Vulnerability-Lookup](https://github.com/vulnerability-lookup/vulnerability-lookup),
or connect it to any software that works with the CVE Record Format.

The project currently targets **CVE Record Format 5.2.0**. Its schema tooling
also tracks the **GCVE BCP-05 1.7** extension profile so that GCVE-specific
authoring and validation can be added incrementally. GCVE support is a future
direction, not yet a claim of complete compatibility.

> [!NOTE]
> Vulniverse is under active development. The editor and API are usable, but
> interfaces and deployment instructions may change before the first stable
> release.

## Why Vulniverse?

- **Guided record authoring** — edit metadata and descriptions in focused
  sections, with a schema-driven editor for the rest of the CVE record.
- **Purpose-built complex-field editors** — work with affected products,
  references, ADP containers, and CVSS 2.0, 3.0, 3.1, and 4.0 metrics without
  having to manipulate their JSON structure by hand.
- **Full-fidelity JSON access** — inspect or replace the complete document in
  the Advanced JSON view. Properties not understood by the guided UI remain in
  the underlying record instead of being discarded.
- **Official-schema validation** — validate against the bundled CVE 5.2.0
  schema and receive errors with record paths and useful messages.
- **Draft-friendly workflow** — incomplete records can be saved as drafts;
  non-draft records are rejected by the API when they do not validate.
- **Reusable integration surface** — ship the UI as a framework-independent
  `<vulniverse-editor>` custom element and provide its persistence through the
  `EditorRepository` contract.
- **Small standalone service** — the Flask REST API loads, creates, updates,
  validates, and stores records in SQLite, making local evaluation simple.
- **Schema-derived UI** — generated authoring and UI schemas keep the forms
  tied to upstream formats while a versioned layout controls presentation.

## Architecture

```text
Vulniverse
├── frontend/                  Vue 3 + TypeScript application
│   ├── standalone app         Vite development and production build
│   └── <vulniverse-editor>    embeddable Web Component build
├── backend/                   Flask JSON API + SQLite persistence
└── schemas/
    ├── upstream/              pinned CVE and GCVE source schemas
    ├── generated/             authoring schema, UI schema, and field index
    └── editor/                human-maintained editor layout
```

The editor does not require a particular host application's data model. An
`EditorRepository` implementation supplies four operations—load, create,
update, and validate—so an integration can use the included HTTP API or adapt
those operations to its own service. The standalone application uses the
included `HttpRepository` and the `/api/v1` endpoints.

## Current scope

| Capability | Status |
| --- | --- |
| Create and edit CVE 5.2.0 records | Available |
| Guided and schema-generated forms | Available |
| Advanced whole-record JSON editing | Available |
| CVE 5.2.0 schema validation | Available |
| Draft persistence through the REST API | Available |
| Embeddable Web Component build | Available |
| GCVE BCP-05 profile/schema tracking | Foundation available |
| Complete GCVE authoring and semantic validation | Planned |
| External publication integrations | Planned |

## Prerequisites

- [Node.js](https://nodejs.org/) 22.18 or newer (Node 24.12+ is also
  supported) and npm
- Python 3.12
- [uv](https://docs.astral.sh/uv/)

## Run locally

### 1. Install and start the backend

```bash
cd backend
uv sync
uv run flask --app vulniverse_api db upgrade
uv run flask --app vulniverse_api run --debug
```

The API listens on `http://127.0.0.1:5000` by default. The development database
is stored in the Flask instance directory.

### 2. Install and start the frontend

In another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5173`. During development, Vite proxies `/api` requests
to the Flask server. A stored record can be opened at
`/editor/<record-id>` (for example, `/editor/CVE-2026-99999`).

## REST API

All included endpoints are rooted at `/api/v1`:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/records/{identifier}` | Load a stored record |
| `POST` | `/records` | Create a record |
| `PUT` | `/records/{identifier}` | Update a record |
| `POST` | `/validate` | Validate a record without saving it |

Create, update, and validation requests use an envelope containing `record`
and `profile`; persistence requests also accept `isDraft`. For example:

```json
{
  "profile": "cve-5.2.0",
  "isDraft": true,
  "record": {
    "dataType": "CVE_RECORD",
    "dataVersion": "5.2.0",
    "cveMetadata": {
      "cveId": "CVE-2026-99999"
    },
    "containers": {
      "cna": {
        "descriptions": [],
        "affected": [],
        "references": []
      }
    }
  }
}
```

## Embed the editor

Build the ES module containing the Web Component:

```bash
cd frontend
npm ci
npm run build:element
```

The output is written to `frontend/dist/element/vulniverse-editor.js`. Import
that module in the host application and render the custom element:

```html
<script type="module" src="/assets/vulniverse-editor.js"></script>

<vulniverse-editor
  mode="edit"
  record-id="CVE-2026-99999"
></vulniverse-editor>
```

The element accepts `mode` (`create` or `edit`), `record-id`, and a
`repository` object implementing `EditorRepository`. It emits `ready`,
`loaded`, `error`, and `dirtyChange` events so a host such as
Vulnerability-Lookup can coordinate navigation, notifications, and unsaved
changes. Because `repository` is an object property rather than a string HTML
attribute, integrations normally assign it from JavaScript:

```js
const editor = document.querySelector("vulniverse-editor");

editor.repository = myVulnerabilityRepository;
editor.addEventListener("dirtyChange", (event) => {
  // Integrate with the host application's leave-page warning.
  console.log("Record changed:", event.detail[0]);
});
```

See `frontend/src/editor/contracts.ts` for the TypeScript repository contract
and record types. The included `HttpRepository` is also a useful reference for
adapting the editor to an existing API.

## Schema workflow

Pinned upstream sources and their provenance live in `schemas/upstream/`; the
active versions are declared in `schemas/manifest.json`. To change how fields
are grouped and presented, edit `schemas/editor/cve.layout.json`, then rebuild
the generated editor artifacts:

```bash
python3 scripts/generate_editor_schemas.py
```

To refresh the pinned schemas from their configured upstream sources, run:

```bash
python3 scripts/update_schemas.py
```

Review upstream changes and regenerated files before committing them.

## Development checks

```bash
# Frontend type-check and production build
cd frontend
npm run build

# Frontend lint (the configured command applies safe fixes)
npm run lint

# Backend tests
cd ../backend
uv run pytest
```

## Project direction

Vulniverse aims to make structured vulnerability authoring a component rather
than a silo. The immediate focus is a robust CVE 5.2.0 workflow and clean
integration into Vulnerability-Lookup and similar platforms. The schema
profile architecture provides a path toward GCVE extensions and additional
semantic checks while preserving interoperability with software that already
consumes CVE records.
