---
icon: lucide/view
---

# Embedding: Vulnerability-Lookup

[Vulnerability-Lookup](https://github.com/vulnerability-lookup/vulnerability-lookup)
(VL) is the reference example of embedding `<vulniverse-editor>` into a
host application that has its own backend, its own record storage, and its
own authentication — none of which Vulniverse's own backend is involved in
at all. This page describes exactly how that integration is wired up.

## Where the pieces live

Everything VL-specific lives in the `vulnerability-lookup` repository, not
in Vulniverse:

- `website/web/static/vulniverse/vulniverse-editor.js` — the built custom
  element, copied in from `frontend/dist/element/vulniverse-editor.js`
  after running `npm run build:element` (see [Get
  started](../setup/setup.md)).
- `website/web/static/vulniverse/repository.js` — VL's own
  `EditorRepository` implementation, `VulnerabilityLookupRepository`.
- `website/web/static/vulniverse/gcve-reservation-panel.js`,
  `cna-publication-panel.js`, `view-vulnerability-module.js` — VL-specific
  `EditorPanel`/`EditorModule` implementations (see
  [Architecture](../development/architecture.md) for what those are).
- `website/web/templates/vulniverse/index.html` — the page template that
  imports all of the above and constructs the `<vulniverse-editor>`
  element.
- `website/web/views/user.py` — the Flask views that render that template.

## The repository: talking to VL's own backend, not Vulniverse's

`VulnerabilityLookupRepository` implements `EditorRepository` against VL's
own CNA API (`website/web/api/v1/cna.py`, mounted at `/api/cna`), not
Vulniverse's `/api/v1`. A few real constraints of that API shape through
into the adapter:

- VL's local source only stores GCVE-format records, so `loadRecord`
  always reports `profile: "gcve-bcp-05-1.7"`.
- The CNA API has no draft concept — POST/PUT validate and persist
  immediately — so every load/create/update reports `isDraft: false`.
  This also hides the editor's "Publish" button, since it only appears
  when `isDraft` is `true`.
- The CNA API has no standalone validation endpoint, so `validateRecord`
  throws rather than fabricating a fake "valid" result; the real
  validation happens server-side on save.
- `getReferenceList` is implemented, but not against Vulniverse's
  CWE/CAPEC proxy — VL already indexes the full CWE and CAPEC lists for
  its own `/cwe`/`/cwes` browsing pages
  (`website/web/api/v1/cwe.py`, `capec.py`), so the repository reuses that
  existing data (`GET /api/cwe/`, `GET /api/capec/`) instead of fetching it
  a second time from MITRE.
- `listTemplates`/`saveTemplate`/`updateTemplate`/`deleteTemplate` are not
  implemented by `VulnerabilityLookupRepository` today. Templates is an
  opt-in panel (`templatesPanel`, imported from the built element bundle
  the same way `gcveIdentifierPanel` is), explicitly included in VL's own
  `editor.panels` — it shows its "this host doesn't support templates"
  message inside VL rather than the create/apply UI.

## Choosing Vulniverse as the editor

VL can run either Vulnogram or Vulniverse as its vulnerability editor,
selected by one config key. `config/generic.json`'s `"editor"` value
(`"vulnogram"` or `"vulniverse"`) is read in `website/web/views/user.py`'s
`vulnogram()` view, which backs the `/submit` and `/edit/<vulnerability_id>`
routes:

```python
if get_config("generic", "editor").strip().lower() == "vulniverse":
    return render_template("vulniverse/index.html", vulnerability_id=vulnerability_id)
# ...otherwise falls through to rendering vulnogram/index.html as before
```

A second pair of routes, `/submit-vulniverse` and
`/edit-vulniverse/<vulnerability_id>` (view function `vulniverse_editor()`
in the same file), always render Vulniverse regardless of that config
value — a direct link to the Vulniverse editor that doesn't depend on
which editor is currently selected as the default.

## Constructing the element

`website/web/templates/vulniverse/index.html` is what actually builds the
element, in a `<script type="module">` block:

```js
const editor = document.createElement("vulniverse-editor");

editor.setAttribute("mode", "{{ 'edit' if vulnerability_id else 'create' }}");
editor.setAttribute("profile", "gcve-bcp-05-1.7");
if (vulnerability_id) {
  editor.setAttribute("record-id", vulnerability_id);
}

editor.repository = new VulnerabilityLookupRepository({ csrfToken });

editor.panels = [
  createGcveReservationPanel({ csrfToken, editUrlBase }),
  // only when the CNA publication feature is configured on this instance:
  createCnaPublicationPanel({ csrfToken }),
  // imported straight from vulniverse-editor.js, same as gcveIdentifierPanel:
  templatesPanel,
];

editor.modules = [
  createViewVulnerabilityModule({ viewUrlBase }),
];

editor.addEventListener("deleted", () => { /* redirect to the recent-activity page */ });
editor.addEventListener("error", (event) => { console.error(event.detail); });

document.getElementById("vulniverse-mount").replaceWith(editor);
```

A few things worth noting precisely:

- `profile` is hardcoded to `"gcve-bcp-05-1.7"` — every record VL creates
  through this editor is authored as GCVE from the start, matching VL's
  own storage constraint mentioned above.
- The static imports (`vulniverse-editor.js`, `repository.js`, the panel/
  module scripts) all run to completion — including the custom element's
  own `customElements.define(...)` side effect — before the rest of this
  script body executes, so `document.createElement("vulniverse-editor")`
  is guaranteed to already produce a real, upgraded element.
- `createGcveReservationPanel` is passed `editUrlBase`, a URL template
  containing the literal placeholder `__VID__` that the panel substitutes
  with a real identifier once one exists (e.g. after reserving a GCVE ID)
  — the same pattern `createViewVulnerabilityModule`'s `viewUrlBase` uses.
- The CNA publication panel is wrapped in a server-side `{% if config.cna %}`
  check, so it's only added when VL's own CNA publication feature is
  configured on that instance.

This is the entire integration surface. Vulniverse's own code — the
component tree in `frontend/src/editor/` — has no VL-specific branches
anywhere; everything described on this page lives on VL's side of the
`EditorRepository`/`EditorModule`/`EditorPanel` boundary.
