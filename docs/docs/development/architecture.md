---
icon: lucide/landmark
---

# Architecture

## Repo structure

```
Vulniverse/
├── frontend/   Vue 3 app — the editor UI
├── backend/    Flask API — record storage, validation, external data proxying
└── schemas/    Vendored CVE/GCVE JSON Schemas — read by both, owned by neither
```

`frontend/` and `backend/` are independent applications. The frontend never
assumes a particular backend exists — every place it needs persistence, it
goes through an abstraction it defines itself, not a hardcoded API call.
That indirection is what makes the editor embeddable, and it's the part of
this page worth reading closely.

## Backend (`backend/`)

A conventional Flask app:

- **App factory** — `create_app()` in `vulniverse_api/__init__.py`.
  SQLAlchemy/Flask-Migrate extensions are instantiated once in
  `extensions.py` and bound to the app here, to avoid circular imports.
- **One blueprint** — `api_bp`, mounted at `/api/v1`. Route modules
  (`api/records.py`, `api/validation.py`, `api/reference_data.py`,
  `api/templates.py`) each register their routes on this same blueprint,
  imported at the bottom of `api/__init__.py` purely for that side effect.
- **SQLite via SQLAlchemy** — `VulnerabilityRecord` stores the whole record
  as a JSON blob (the `document` column); there's no per-field SQL schema,
  because the JSON Schema in `schemas/` is the actual source of truth for
  record shape, not the SQL model. `Template` (`fields` as a JSON column of
  `{path, value}` pairs) follows the same pattern for a different resource.
- **Validation** — `services/record_validation.py` resolves which schema
  to validate against from `schemas/manifest.json`, keyed by the record's
  `profile` (`cve-5.2.0` or `gcve-bcp-05-1.7`), compiles it with
  `jsonschema`, and caches each compiled validator with `lru_cache`. Drafts
  (`isDraft: true`, the default) skip validation on save; only non-draft
  records are checked before being stored. See [GCVE (BCP-05)
  support](#gcve-bcp-05-support) below for the profile-specific rules layered
  on top of plain schema validation.
- **Proxying external data** — `services/reference_data.py` is the pattern
  for anything the backend needs from an outside source: fetch once, cache
  in-memory for a fixed period, serve a trimmed shape to the frontend, and
  fall back to the last successful result rather than failing outright if a
  refresh errors. Used today for MITRE's CWE/CAPEC lists.

## Frontend (`frontend/`)

Two build entry points share the same Vue component tree:

- **`src/main.ts`** — the standalone SPA (Vue Router + Pinia), built via
  `vite.config.ts`. Adds routing and a couple of pages around the editor.
- **`src/element.ts`** — registers `<vulniverse-editor>` as a native Web
  Component via Vue's `defineCustomElement`, wrapping
  `src/editor/VulniverseEditor.ce.vue`. Built separately
  (`vite.element.config.ts`) into one self-contained
  `dist/element/vulniverse-editor.js` — CSS inlined, images base64'd, no
  external dependencies.

Both entry points render the *same* `VulniverseEditor.ce.vue` component and
the same section/renderer components beneath it. The custom element is that
component alone, wearing a `<script>`-tag hat; the SPA is that component
plus routing.

### The `EditorRepository` contract

`src/editor/contracts.ts` defines the interface `VulniverseEditor.ce.vue`
uses for all persistence — it never calls `fetch` directly itself:

```ts
interface EditorRepository {
  loadRecord(identifier): Promise<LoadedRecord>;
  createRecord(record, profile, isDraft): Promise<LoadedRecord>;
  updateRecord(identifier, record, profile, isDraft): Promise<LoadedRecord>;
  validateRecord(record, profile): Promise<ValidationResult>;
  deleteRecord(identifier): Promise<void>;

  // Optional — a renderer checks for these before using them, and
  // degrades to a simpler behavior (plain free-text entry, a
  // "not supported here" message) when they're absent:
  getReferenceList?(kind: "cwe" | "capec"): Promise<ReferenceListItem[]>;
  listTemplates?(): Promise<Template[]>;
  saveTemplate?(name, fields): Promise<Template>;
  updateTemplate?(id, name, fields): Promise<Template>;
  deleteTemplate?(id): Promise<void>;
}
```

`VulniverseEditor.ce.vue` takes a `repository` **prop** of this shape and
is otherwise unaware of HTTP. `src/repositories/HttpRepository.ts` is *one*
implementation — the one the standalone app passes in, calling Vulniverse's
own `/api/v1/...` endpoints. A host embedding the editor supplies its own
implementation instead, talking to whatever backend it already has; see
[Embedding: Vulnerability-Lookup](../embedding/vl.md) for a real one.

The optional methods follow the same idea one level deeper: the interface
declares them optional, the calling component checks for their existence
(`repository.value?.getReferenceList`), and a repository that doesn't
implement one simply doesn't get that feature — nothing else breaks.

### `EditorModule` and `EditorPanel`

Two more host-configurable extension points, both passed as props to
`VulniverseEditor.ce.vue` alongside `repository`:

- **`EditorModule[]`** (`modules` prop) — an extra button in the editor's
  header (e.g. a "View published page" button that only makes sense inside
  a particular host). Each has `id`, `label`, an optional `isVisible`/
  `isEnabled`, and a `run(context)` action.
- **`EditorPanel[]`** (`panels` prop) — an extra tab in the sidebar, each
  backed by a whole Vue component the host supplies. Has `id`, `label`, a
  `component`, and an optional `isVisible`.

Both receive the same `EditorModuleContext` (`identifier`, `profile`,
`record`, `isDraft`) as a plain prop — not via Vue's `provide`/`inject` —
so a panel authored by a host with no build step of its own still works,
as long as it's built from the same Vue primitives Vulniverse re-exports
from `src/element.ts` (`defineComponent`, `h`, `ref`, `onMounted`, `watch`),
bound to the *same* Vue instance the element itself uses.

## Schema tooling (`schemas/`, `scripts/`)

- `schemas/upstream/` holds vendored CVE/GCVE schemas fetched from their
  canonical sources, refreshed by `scripts/update_schemas.py`. Each vendored
  version carries a `SOURCE.json` recording where it came from and when.
- `schemas/manifest.json` declares which profiles exist and which schema
  version is "current" per kind (`cve`, `gcve`).
- `scripts/generate_editor_schemas.py` reads the active profile's upstream
  schema plus `schemas/editor/cve.layout.json` (the human-maintained
  section/field layout) — and, for the `gcve` profile kind specifically,
  also `schemas/editor/gcve.layout-extra.json`, which adds a "GCVE
  extension" section for the `x_gcve` field on top of the base CVE layout —
  and writes, per profile, into `schemas/generated/<profile>/`: a
  dereferenced `authoring.schema.json`, a JSONForms `ui.schema.json`, a
  full field catalog `fields.json`, and a `generation-report.json`.
  `authoring.schema.json` and `ui.schema.json` are also copied into
  `frontend/src/generated/schemas/<profile>/` for the frontend to import
  directly; a trimmed `field-paths.json` (path + title + type only, scalar
  leaves only) is generated straight into the frontend directory instead
  of copying the full `fields.json`, to keep that one small — it backs the
  Templates section's field-path autocomplete.

Regenerating after a layout or schema change is a manual step
(`python3 scripts/generate_editor_schemas.py`), not run in CI — see
[Get started](../setup/setup.md).

## GCVE (BCP-05) support

GCVE authoring and validation is implemented, not just scaffolded — this
is worth spelling out precisely since it's easy to undersell from the repo
structure alone:

- **Schema resolution is profile-driven.** `schemas/manifest.json`
  declares `gcve-bcp-05-1.7` with a `baseSchema` (the same CVE 5.2.0
  schema) plus an `extensionSchemas` entry pointing at the vendored
  `upstream/gcve/bcp-05/1.7/gcve-bcp-05.schema.json`. Both
  `record_validation.py`'s validator and `generate_editor_schemas.py`
  resolve these paths from the manifest at the given profile id, not from
  a hardcoded CVE-only path.
- **`schemas/overlays/gcve-bcp-05-1.7.json`** exists specifically to
  legalize a root-level `x_gcve` property against the base CVE schema's
  `additionalProperties: false` — merged into both root `oneOf` branches
  before compiling. It's deliberately loose; the vendored GCVE schema
  remains the sole authority on real strictness for what's inside
  `x_gcve` itself.
- **BCP-05 semantic rules are enforced**, on top of plain schema
  validation, by `validate_gcve_semantics()` in
  `services/record_validation.py`: a non-empty `relationships` array is
  required for ten specific `recordType`s (`update`, `analysis`,
  `metadata`, `reference`, `comment`, `statement`, `remediation`,
  `deprecation`, `detection`, `translation`), `language` is additionally
  required when `recordType` is `translation`, and a `relationships[].type`
  outside BCP-05's recommended set produces a warning (not a blocking
  error). `x_gcve` is checked wherever it appears in the document —
  BCP-05's own "location-agnostic" rule — not only at the record root.
- **The frontend has a dedicated `x_gcve` editor** —
  `frontend/src/editor/renderers/GcveExtensionRenderer.vue` — for adding,
  removing, and editing GCVE extension entries (`vulnId`, `recordType`,
  `language`, and a nested `relationships` list), registered in
  `renderers/index.ts` and reachable via the "GCVE extension" section that
  `gcve.layout-extra.json` adds for this profile.
- **Creating a record as GCVE is a first-class option in the standalone
  app**, not something only an embedding host can request:
  `frontend/src/pages/NewRecordPage.vue` offers "Create as CVE" and
  "Create as GCVE" (from `frontend/src/editor/profiles.ts`) before
  handing off to the editor with the chosen `profile`;
  `VulniverseEditor.ce.vue` seeds a new record's `x_gcve: []` whenever the
  profile starts with `gcve-`.

This covers the semantic rules above, not a full audit against every rule
in the BCP-05 specification text — if a BCP-05 rule isn't listed here, it
isn't necessarily enforced.
