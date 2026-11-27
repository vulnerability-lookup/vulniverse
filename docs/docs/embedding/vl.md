---
icon: lucide/view
---

# Embedding: Vulnerability-Lookup

[Vulnerability-Lookup](https://github.com/vulnerability-lookup/vulnerability-lookup)
(VL) is the reference example of embedding `<vulniverse-editor>` into a
host application that has its own backend, its own record storage, and its
own authentication — Vulniverse's own backend is not involved in storing or
validating records at all. (Patch2Vuln is the one exception: VL's own
backend calls that external service directly too, independently of
Vulniverse — see below.) This page describes exactly how that integration
is wired up; for the element's general props/contract reference (not
VL-specific), see [The `<vulniverse-editor>` element](element.md).

## Where the pieces live

Everything VL-specific lives in the `vulnerability-lookup` repository, not
in Vulniverse:

| File | What it is |
| --- | --- |
| `package.json`, `tools/copy_frontend_assets.py` | The editor itself, as the npm package `@nmd03/vulniverse` (pinned to an exact version). `npm ci` installs it and copies `vulniverse-editor.js` to `website/web/static/npm_components/@nmd03/vulniverse/dist/`, where the template and panels import it from. |
| `website/web/static/vulniverse/repository.js` | VL's own `EditorRepository` implementation, `VulnerabilityLookupRepository`. |
| `website/web/static/vulniverse/gcve-id.js` | Reads and writes a record's GCVE ID: `x_gcve[].vulnId` in the CNA container, with the legacy `cveMetadata.vulnId` as a fallback. Shared by the repository and both VL panels. |
| `website/web/static/vulniverse/gcve-reservation-panel.js`, `cna-publication-panel.js`, `view-vulnerability-module.js` | VL-authored `EditorPanel`/`EditorAction` implementations — see [Custom panels and actions](#custom-panels-and-actions) below. |
| `website/web/templates/vulniverse/index.html` | The page template that imports all of the above and constructs the `<vulniverse-editor>` element. |
| `website/web/views/vulnerability_editor.py` | The Flask blueprint whose views render that template. |
| `website/web/api/v1/vulniverse_templates.py`, `vulniverse_record_quality.py`, `patch2vuln.py` | VL's own backend routes for the Templates, Record Quality, and Patch2Vuln panels respectively (`website/web/services/patch2vuln_service.py` and `website/lib/patch2vuln_access.py` back the last one). |

## Updating the editor

In the `vulnerability-lookup` checkout:

```bash
npm install --save-exact @nmd03/vulniverse@1.0.1   # the new version
python3 tools/copy_frontend_assets.py               # npm install <package> skips postinstall
poetry run pytest -q tests/test_static_assets.py && npm test
```

Reload the editor page, check that it loads, saves and reserves a GCVE
ID, then commit `package.json` and `package-lock.json`. Servers pick the
new version up with their usual update (`npm ci --omit=dev`, or
`poetry run update`).

## Where and how it's mounted

The editor lives in its own blueprint,
`website/web/views/vulnerability_editor.py` (URL prefix `/vuln`):

| Route | What it is |
| --- | --- |
| `/vuln/create` | The editor, for a new vulnerability |
| `/vuln/<vulnerability_id>/edit` | The editor, for an existing vulnerability |

Both need a logged-in user with the right permission. Two settings in
`config/website.py` decide whether and which editor is served (read in
`website/web/vulnerability_editor.py`):

- `WEB_MODULES["vulnerability_editor"]` turns the editor on. It's off by
  default; with it off, these routes don't exist.
- `VULNERABILITY_EDITOR` chooses the editor: `"vulniverse"` (the default)
  renders `vulniverse/index.html`, `"vulnogram"` the older Vulnogram
  editor. Any other value stops VL at start-up.

The old `/submit` and `/edit/<vulnerability_id>` URLs
(`website/web/views/user.py`) are permanent (301) redirects to these.

Whichever route renders it, `website/web/templates/vulniverse/index.html`
does the actual mounting: it has a `<div id="vulniverse-mount"></div>`
placeholder in its body, and a `<script type="module">` block that builds
a `<vulniverse-editor>` element and swaps it in:

```js
const editor = document.createElement("vulniverse-editor");
// ...set attributes, repository, panels, actions (see below)...
document.getElementById("vulniverse-mount").replaceWith(editor);
```

## The repository: talking to VL's own backend, not Vulniverse's

`VulnerabilityLookupRepository` implements `EditorRepository` against VL's
own CNA API (`website/web/api/v1/cna.py`, mounted at `/api/cna`) for
record storage, plus a handful of VL's other own API namespaces for the
optional panels below — none of it Vulniverse's `/api/v1`. A few real
constraints of the CNA API's shape through into the adapter:

- VL's local source only stores GCVE-format records, so `loadRecord`
  always reports `profile: "gcve-bcp-05-1.7"`.
- The CNA API has no draft concept — POST/PUT validate and persist
  immediately — so every load/create/update reports `isDraft: false`.
  `VulnerabilityLookupRepository` sets `lifecycleTransitions = []`
  explicitly in its constructor for the same reason, so the editor shows
  no Publish/Revert-to-draft button at all — there is nowhere for either
  to persist an intermediate state to. See [The
  repository](repository.md#draft-and-publish-buttons) for what an unset vs. an explicit empty
  `lifecycleTransitions` means in general.
- `validateRecord` POSTs the record to VL's own
  `/api/vulnerability/validate`, which checks it the GCVE way. The editor
  has no notion of a warning, so when the record is invalid its warnings
  are listed after its errors, each prefixed `Warning:`; a valid record
  reports nothing.
- `getReferenceList`, `searchCpeVendors`/`searchCpeProducts`/`searchCpes`,
  `listTemplates`+CRUD, and `scoreRecordQuality` are all implemented
  (`scoreRecordQuality` is no longer called from Vulniverse 1.1 on, see
  below). The
  CWE/CAPEC/CPE lookups are gated behind the `features` the repository
  was constructed with (see [Configuring panels, actions, and
  features](#configuring-panels-actions-and-features) below). CWE/CAPEC
  reuse VL's own already-indexed lists for its `/cwe`/`/capec` browsing
  pages (`website/web/api/v1/cwe.py`, `capec.py`) rather than fetching
  MITRE's data a second time; CPE vendor/product/entry lookups proxy to
  VL's own `/api/cpe_editor` routes, default **off** (see that route's own
  tradeoffs — a live call per keystroke to an external CPE Editor
  instance). Those routes only exist when `cpe.cpe_enabled` is set in
  VL's config (`website/web/api/v1/__init__.py`).
- `submitPatch2VulnJob`/`getPatch2VulnJob` call VL's own `/api/patch2vuln`
  routes, which in turn call an external Patch2Vuln web service directly
  — configured via `config/patch2vuln.json` in VL, entirely independent of
  Vulniverse's own `config/vulniverse.toml`'s `[panels.patch2vuln]`. A
  patch2vuln job's "jobId" handed back to the frontend is a signed token
  binding it to the submitting user (`website/lib/patch2vuln_access.py`),
  so one VL user can't poll or read another's in-progress analysis.

## Custom panels and actions

`editor.panels`/`editor.actions` mix two kinds of entries — VL's own,
purpose-built for its backend, and Vulniverse's built-ins reused as-is:

| Entry | Source | Kind | What it needs |
| --- | --- | --- | --- |
| `createGcveReservationPanel({csrfToken, editUrlBase})` | VL-authored (`gcve-reservation-panel.js`) | `EditorPanel` | VL's own reservation endpoints directly — not part of `EditorRepository` |
| `createCnaPublicationPanel({csrfToken})` | VL-authored (`cna-publication-panel.js`) | `EditorPanel` | Same — talks to VL's CNA publication backend directly |
| `createViewVulnerabilityModule({viewUrlBase})` | VL-authored (`view-vulnerability-module.js`) | `EditorAction` | A link to the published record's VL page — no repository method |
| `downloadAction`, `tutorialAction` | Reused from `vulniverse-editor.js` | `EditorAction` | Nothing — the record as JSON/HTML/PDF, and a guided tour |
| `templatesPanel` | Reused from `vulniverse-editor.js` | `EditorPanel` | `listTemplates` + CRUD (implemented, see above) |
| `recordQualityPanel` | Reused from `vulniverse-editor.js` | `EditorPanel` | Nothing from Vulniverse 1.1 on: it scores in the browser, so `vulniverse_record_quality.py` and `scoreRecordQuality` are unused and can go. Before 1.1, `scoreRecordQuality` |
| `patch2vulnPanel` | Reused from `vulniverse-editor.js` | `EditorPanel` | `submitPatch2VulnJob` + `getPatch2VulnJob` (implemented) |

`createGcveReservationPanel` and `createCnaPublicationPanel` also take an
optional `apiRoot` (defaults `/api/cna` and `/publications`). Likewise,
`VulnerabilityLookupRepository`'s constructor takes, besides `csrfToken`
and `features`, optional base URLs for each backend it talks to:
`apiRoot` (`/api/cna`), `referenceApiRoot` (`/api`), `cpeApiRoot`,
`templatesApiRoot`, `recordQualityApiRoot`, and `patch2vulnApiRoot`.

The VL-authored ones bypass `EditorRepository` entirely and call VL's own
endpoints directly from inside the panel component — they exist because
GCVE reservation and CNA publication aren't part of the generic
`EditorRepository` contract's "implement this and the built-in panel
works" model the way Templates/Record Quality/Patch2Vuln are. See
[Architecture](../development/architecture.md) for what `EditorPanel`/
`EditorAction` are in general.

## Configuring panels, actions, and features

VL mirrors Vulniverse's own `config/vulniverse.toml` pattern with its own
`config/vulniverse.json` (copy `config/vulniverse.json.sample` to get
started — same fallback behavior: no real file means the sample's values
apply):

```json
{
  "panels": {
    "gcve-reservation": true,
    "cna-publication": true,
    "templates": true,
    "record-quality": true,
    "patch2vuln": true
  },
  "actions": {
    "view-vulnerability": true,
    "download": true,
    "tutorial": true
  },
  "features": {
    "cpeVendors": false,
    "cpeProducts": false,
    "cpeEntries": false,
    "cwe": true,
    "capec": true
  }
}
```

A panel/action id (or a whole section) absent from this file takes its
value from `config/vulniverse.json.sample` — the merge happens in
`website/web/vulnerability_editor.py`'s `vulniverse_settings()`.
`cna-publication` additionally requires `generic.cna` to be true
regardless of this setting. `features` gates which CPE/CWE/CAPEC
autocomplete lookups `repository.js` is allowed to perform — CPE lookups
default off since they call out to an external CPE Editor instance per
keystroke; enable them only after reviewing that tradeoff for unpublished
records.

Patch2Vuln additionally needs its own `config/patch2vuln.json`
(`patch2vuln_enabled`, `patch2vuln_url`, `patch2vuln_timeout`, `api_key`)
to actually reach a Patch2Vuln web service — the panel is only included
when both `patch2vuln_enabled` there and `panels.patch2vuln` above are
true.

Every panel/action entry in `index.html` is individually wrapped in its
own `{% if config.vulniverse.panels['id'] %}`/`actions['id']` Jinja check
corresponding to this file.

## Constructing the element

Putting the pieces above together, `index.html`'s script block:

```js
import { downloadAction, patch2vulnPanel, recordQualityPanel, templatesPanel, tutorialAction } from ".../vulniverse-editor.js";
import { VulnerabilityLookupRepository } from ".../repository.js";
import { createGcveReservationPanel } from ".../gcve-reservation-panel.js";
import { createViewVulnerabilityModule } from ".../view-vulnerability-module.js";
import { createCnaPublicationPanel } from ".../cna-publication-panel.js";

const csrfToken = "{{ csrf_token() }}";
const editor = document.createElement("vulniverse-editor");

editor.setAttribute("mode", "{{ 'edit' if vulnerability_id else 'create' }}");
editor.setAttribute("profile", "gcve-bcp-05-1.7");
if (vulnerability_id) {
  editor.setAttribute("record-id", vulnerability_id);
}

editor.repository = new VulnerabilityLookupRepository({
  csrfToken,
  features: {{ config.vulniverse.features | tojson }},
});

editor.panels = [
  createGcveReservationPanel({ csrfToken, editUrlBase }), // {% if panels['gcve-reservation'] %}
  createCnaPublicationPanel({ csrfToken }),                // {% if config.cna and panels['cna-publication'] %}
  templatesPanel,                                          // {% if panels['templates'] %}
  recordQualityPanel,                                       // {% if panels['record-quality'] %}
  patch2vulnPanel,                                           // {% if config.patch2vuln_enabled and panels['patch2vuln'] %}
];

editor.actions = [
  createViewVulnerabilityModule({ viewUrlBase }), // {% if actions['view-vulnerability'] %}
  downloadAction,                                 // {% if actions['download'] %}
  tutorialAction,                                 // {% if actions['tutorial'] %}
];

editor.addEventListener("deleted", () => { /* redirect to the recent-activity page */ });
editor.addEventListener("error", (event) => { console.error(event.detail); });

// The first save gives a new record its id: show its edit URL, without a reload.
editor.addEventListener("loaded", (event) => {
  const [identifier] = event.detail ?? [];
  if (!identifier) return;
  const editUrl = editUrlBase.replace("__VID__", encodeURIComponent(identifier));
  if (location.pathname !== new URL(editUrl, location.href).pathname) {
    history.replaceState(null, "", editUrl);
  }
});

document.getElementById("vulniverse-mount").replaceWith(editor);
```

A few things worth noting precisely:

- `profile` is hardcoded to `"gcve-bcp-05-1.7"` — every record VL creates
  through this editor is authored as GCVE from the start, matching VL's
  own storage constraint mentioned above.
- The static imports (`vulniverse-editor.js`, `repository.js`, the panel/
  action scripts) all run to completion — including the custom element's
  own `customElements.define(...)` side effect — before the rest of this
  script body executes, so `document.createElement("vulniverse-editor")`
  is guaranteed to already produce a real, upgraded element.
- `createGcveReservationPanel` is passed `editUrlBase`, a URL template
  containing the literal placeholder `__VID__` that the panel substitutes
  with a real identifier once one exists (e.g. after reserving a GCVE ID)
  — the same pattern `createViewVulnerabilityModule`'s `viewUrlBase` uses.

This is the entire integration surface. Vulniverse's own code — the
component tree in `frontend/src/editor/` — has no VL-specific branches
anywhere; everything described on this page lives on VL's side of the
`EditorRepository`/`EditorAction`/`EditorPanel` boundary.
