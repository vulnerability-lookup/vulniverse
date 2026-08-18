# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project purpose

Vulniverse is a standalone web application for editing vulnerability records (CVE / GCVE format) that can be exported and embedded into [Vulnerability-Lookup](https://github.com/vulnerability-lookup/vulnerability-lookup). It has two independent halves:

```
Vulniverse
├── frontend/  Vue 3 editor
│   ├── standalone web application (src/App.vue + views/)
│   └── embeddable <vulniverse-editor> custom element (src/element.ts)
│
└── backend/   Flask API
    ├── record storage (SQLite via SQLAlchemy)
    ├── JSON Schema validation against upstream CVE/GCVE schemas
    ├── CPE Editor proxy (not yet implemented)
    └── external publication integrations (not yet implemented)
```

`schemas/` at the repo root holds the upstream CVE 5.2.0 and GCVE schemas used by backend validation (see Schemas below) — it is shared by the backend and is not part of either app's own source tree.

## Commands

### Backend (`backend/`, uv + Flask)

```bash
uv sync                        # install deps
uv run flask --app vulniverse_api run --debug   # run dev server (port 5000)
uv run pytest                                    # run all tests
uv run pytest tests/path_to_test.py::test_name   # run a single test
uv run ruff check .        # lint
uv run mypy .              # type-check
uv run flask --app vulniverse_api db migrate -m "message"  # generate an Alembic migration
uv run flask --app vulniverse_api db upgrade               # apply migrations
```

### Frontend (`frontend/`, Vite + Vue 3 + TypeScript)

```bash
npm install
npm run dev                    # dev server on :5173, proxies /api to http://127.0.0.1:5000
npm run build                  # type-check + production build of the standalone app
npm run build:element          # build the embeddable <vulniverse-editor> custom element to dist/element
npm run test:unit               # Vitest
npm run test:unit -- HelloWorld # run a single Vitest file/pattern
npm run test:e2e                # Playwright (run `npm run build` first if testing against a prod build)
npm run test:e2e -- tests/example.spec.ts   # single e2e spec
npm run lint                    # oxlint + eslint, both with --fix
npm run format                  # prettier --write on src/
```

The backend must be running on `127.0.0.1:5000` for the frontend dev proxy (`/api` → backend) to work.

## Backend architecture

- App factory: `create_app()` in `backend/src/vulniverse_api/__init__.py`. SQLAlchemy/Flask-Migrate extensions are instantiated once in `extensions.py` (`db`, `migrate`) and bound to the app in the factory to avoid circular imports.
- SQLite database lives at `backend/src/instance/vulniverse.sqlite` (instance-relative config); this path and `backend/instance/` are gitignored.
- All routes are registered on a single blueprint `api_bp` (`api/__init__.py`), mounted at `/api/v1`. Route modules (`records.py`, `validation.py`) are imported at the bottom of `api/__init__.py` *after* `api_bp` is defined, purely for their side effect of registering routes on it — new route modules must follow the same import-at-bottom pattern.
- `VulnerabilityRecord` (`models.py`) stores the full record as a JSON blob (`document` column) alongside `identifier`, `profile`, and `is_draft`. There's no per-field schema in the DB — the JSON Schema in `schemas/` is the source of truth for record shape, not the SQL model.
- Record identifiers are derived from the record body itself (`cveMetadata.vulnId` or `cveMetadata.cveId`), not client-supplied — see `extract_identifier` in `api/records.py`.
- Validation (`services/record_validation.py`) loads the bundled CVE 5.2.0 schema from `schemas/upstream/cve/5.2.0/CVE_Record_Format_bundled.json` (path resolved relative to the repo root via `PROJECT_ROOT = Path(__file__).parents[4]` — moving this file changes that offset) and caches the compiled `jsonschema` validator with `lru_cache`. Profiles prefixed `gcve-` additionally run `validate_gcve_semantics`, currently a stub to be filled in incrementally.
- Drafts (`isDraft: true`, the default) skip schema validation on save so incomplete records can be persisted; only non-draft records are validated against the schema before being stored (`POST /api/v1/records`).
- Migrations use Flask-Migrate/Alembic (`backend/migrations/`), single-database config.

## Frontend architecture

- Two build entry points share the same Vue components:
  - `src/main.ts` — the standalone SPA (Vue Router + Pinia), built via `vite.config.ts`.
  - `src/element.ts` — registers `<vulniverse-editor>` as a native custom element (via `defineCustomElement`) wrapping `src/editor/VulniverseEditor.ce.vue`, built separately via `vite.element.config.ts` into `dist/element`. Files ending in `.ce.vue` are treated as custom elements by the `vue()` plugin (`customElement: /\.ce\.vue$/`).
- `src/editor/contracts.ts` defines the `EditorRepository` interface — the boundary between the editor UI and whatever backend it talks to (`getCapabilities`, `loadRecord`, `createRecord`, `updateRecord`, `validateRecord`). `VulniverseEditor.ce.vue` is host-agnostic: it receives a `repository` prop implementing this interface and doesn't know about HTTP.
- `src/repositories/HttpRepository.ts` is the concrete `EditorRepository` implementation used by the standalone app; it talks to `/api/v1/...`. Because the custom element depends only on the `EditorRepository` contract, an embedding host app can supply its own repository implementation instead (e.g. to talk to Vulnerability-Lookup's own backend directly).
- `updateRecord` on `HttpRepository` is currently unimplemented (throws) — there is no update endpoint on the backend yet, only create (`POST /records`) and read (`GET /records/<id>`).
- Path alias `@` → `frontend/src` (configured in `vite.config.ts` and the tsconfigs).
- Most of `src/components/` (`HelloWorld.vue`, `TheWelcome.vue`, icons, `stores/counter.ts`) and the `About`/`Home` views are unmodified Vue CLI scaffold, not application logic — don't treat them as architectural examples for new work.

## Schemas

`schemas/manifest.json` declares validation *profiles* and how they compose:

```json
{
  "profiles": {
    "cve-5.2.0": { "baseSchema": "upstream/cve/5.2.0/CVE_Record_Format_bundled.json" },
    "gcve-bcp-05-1.7": {
      "baseSchema": "upstream/cve/5.2.0/CVE_Record_Format_bundled.json",
      "extensionSchemas": ["upstream/gcve/bcp-05/1.7/gcve-bcp-05.schema.json"],
      "semanticValidator": "gcve-bcp-05"
    }
  }
}
```

- `upstream/` holds vendored schemas fetched from their canonical sources (CVE Record Format, GCVE BCP-05) and should be treated as read-only/generated, not hand-edited.
- `overlays/` and `generated/` exist for profile-specific overlays and derived/bundled schema output but are currently empty — the backend's `record_validation.py` does not yet read the manifest or these directories; it hardcodes the CVE 5.2.0 schema path directly. When wiring up additional profiles (e.g. GCVE), prefer resolving schema paths through `manifest.json` rather than adding more hardcoded paths.
