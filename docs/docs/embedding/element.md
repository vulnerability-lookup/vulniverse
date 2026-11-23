---
icon: lucide/puzzle
---

# The `<vulniverse-editor>` element

This is the actual integration surface — everything a host application
configures when embedding the editor, whether that host is
[Vulnerability-Lookup](vl.md) or something else entirely.
`config/vulniverse.toml` (see [Configuration](../setup/config.md)) has no
effect here — it's a standalone-app-only concern; a host decides its own
`panels`/`actions` directly, in its own code.

## Steps to embed it

`frontend/src/editor/` has zero host-specific branches anywhere — every
step below lives entirely on the host's side of the
`EditorRepository`/`EditorPanel`/`EditorAction` boundary. See
[Embedding: Vulnerability-Lookup](vl.md) for a fully worked example of
all of these steps together.

1. **Build the element bundle**:
   ```bash
   cd frontend
   npm run build:element
   ```
   Produces one self-contained file, `dist/element/vulniverse-editor.js`
   — CSS inlined, images base64'd, no external dependencies — plus its
   type declarations, `vulniverse-editor.d.ts`. Copy them into the host
   app's own static assets. Or skip the build: install the npm package, or
   download a released bundle (see
   [Embed it](../quickstart/embed.md#1-get-the-bundle)).

2. **Load it with a static import**:
   ```js
   import { templatesPanel } from "/static/vulniverse/vulniverse-editor.js";
   ```
   Importing it runs `customElements.define("vulniverse-editor", ...)` as
   a side effect. Use a top-level static import, not a dynamic one —
   static imports run to completion before the rest of the script body,
   so `document.createElement("vulniverse-editor")` afterward is
   guaranteed to produce an already-upgraded element.

3. **Implement an `EditorRepository`** against the host's own backend —
   this is the real integration work. See [The repository](repository.md).

4. **Construct the element and set it up**:
   ```js
   const editor = document.createElement("vulniverse-editor");

   editor.setAttribute("mode", vulnerabilityId ? "edit" : "create");
   editor.setAttribute("profile", "gcve-bcp-05-1.7"); // or "cve-5.2.0", "osv-1.9.2"
   if (vulnerabilityId) editor.setAttribute("record-id", vulnerabilityId);

   editor.repository = new MyRepository({ /* ... */ });
   ```
   `mode`/`profile`/`record-id` are plain HTML attributes (strings only).
   `repository` (and `panels`/`actions` below) are always assigned as JS
   properties after `createElement` — never as attribute strings, since
   they're objects/arrays, not strings.

   They can also be set after the element is mounted (step 7), as
   frameworks usually do. In edit mode the editor then shows "Waiting for
   a repository…" and loads the record once `repository` is first set.
   Only the first repository is used; to switch to another, mount a new
   element.

5. **(Optional) Add panels and actions** — see [`panels` and
   `actions`](#panels-and-actions) below:
   ```js
   editor.panels = [myCustomPanel, templatesPanel];
   editor.actions = [myCustomAction];
   ```

6. **Listen for events** — see [Events](#events) below:
   ```js
   editor.addEventListener("loaded", (e) => { /* e.detail[0]: identifier */ });
   editor.addEventListener("error", (e) => console.error(e.detail[0]));
   ```

7. **Mount it**:
   ```js
   document.getElementById("vulniverse-mount").replaceWith(editor);
   ```

8. **(Optional) Theme it** — the shadow-DOM CSS reads a handful of custom
   properties with fallbacks: `--vulniverse-primary`,
   `--vulniverse-primary-rgb`, `--vulniverse-accent-text`,
   `--vulniverse-text`, `--vulniverse-background`, `--vulniverse-muted`,
   `--vulniverse-border`, `--vulniverse-changed`.
   CSS custom properties pierce shadow boundaries, so setting these on
   `:root` (or on the `<vulniverse-editor>` element itself) in the host
   page re-themes the editor's colors without touching its internal
   styles. Skip this if the defaults are fine.

9. **(Optional) Give it a real height** — the element's `:host` rule is
   `height: 100%`, a no-op unless the host page's own CSS gives
   `<vulniverse-editor>` a real, definite height (e.g. a flex/grid
   ancestor). Leave it alone to let it size to its own content instead.

## Props reference

| Prop | Type | Notes |
| --- | --- | --- |
| `mode` | `"create" \| "edit"` | Defaults to `"create"`. |
| `record-id` | `string` | Required when `mode="edit"`. |
| `profile` | `string` | `"gcve-bcp-05-1.7"` (the default), `"cve-5.2.0"`, or `"osv-1.9.2"`. |
| `repository` | `EditorRepository` | Set from JavaScript (`editor.repository = ...`), not an HTML attribute — see below. Before or after mounting; only the first one set is used. |
| `actions` | `EditorAction[]` | Optional extra header buttons. |
| `panels` | `EditorPanel[]` | Optional extra sidebar tabs — see note below. |

## `repository`

`repository` is a plain object, not a string, so it's always assigned from
JavaScript rather than written as an HTML attribute:

```js
const editor = document.querySelector("vulniverse-editor");
editor.repository = myRepository;
```

What it has to implement (four required methods, and optional groups for
deleting, templates, CWE/CPE suggestions, publishing, record quality and
Patch2Vuln), with every signature and data shape: [The
repository](repository.md).

## `panels` and `actions`

```js
editor.panels = [
  myCustomPanel,  // your own object shaped like EditorPanel
  templatesPanel, // reused straight from Vulniverse's own bundle
];

editor.actions = [
  myCustomAction, // your own object shaped like EditorAction
];
```

`EditorPanel`/`EditorAction` (`frontend/src/editor/contracts.ts`) are just
plain object shapes — nothing requires a panel or action to originate from
Vulniverse, so mixing host-authored and Vulniverse-authored entries in the
same array is expected. There's no config file and no
capabilities-filtering step for an embedded host (that machinery —
`config/vulniverse.toml` + `GET /api/v1/capabilities` — is
standalone-app-only, see [Configuration](../setup/config.md)); a host just
decides the array contents directly in its own code.

`src/element.ts` also exports:

- `downloadAction` and `tutorialAction` — built-in `EditorAction`s: the
  record as JSON, HTML or PDF (print dialog), and a short guided tour of
  the editor. Like the panels below, a host adds them to `actions` itself.
- `RecordValidationError` — the error a repository throws from
  `createRecord`/`updateRecord` when the record fails schema validation
  (as opposed to a network failure, a 404, or a conflict).
- `EditorRepositoryError` — an error with an HTTP-style `status` and
  `details`, which the publishing panels read; see
  [The repository](repository.md#errors).
- The types `EditorRepository`, `EditorPanel`, `EditorAction`,
  `EditorContext`, `EditorDocument`, `LoadedRecord`, `ValidationResult`,
  `ValidationError`, `LifecycleTransition` and `ThemePreference`, and
  `VulniverseEditorElement`, the element itself. They ship as
  `vulniverse-editor.d.ts`, next to the bundle and in the npm package. It's
  self-contained (Vue's types aren't needed) and registers the element in
  `HTMLElementTagNameMap`, so `document.createElement("vulniverse-editor")`
  is typed.
- `defineComponent`, `h`, `onMounted`, `ref`, `watch` — a minimal slice of
  Vue's runtime, so a host without a build step of its own can write a
  panel component against the same Vue the bundle uses.

Five built-in panels are exported from `src/element.ts` too — none are baked
into the element itself, so a host has to include each explicitly to get
its UI, but can then reuse it instead of authoring an equivalent from
scratch:

| Panel | Needs repository method(s) |
| --- | --- |
| `templatesPanel` | `listTemplates` + CRUD |
| `cveProgramPanel` | `getCnaPublication` + the publish actions |
| `vulnerabilityLookupPanel` | `getCnaPublication` + the publish actions |
| `recordQualityPanel` | `scoreRecordQuality` |
| `patch2vulnPanel` | `submitPatch2VulnJob` + `getPatch2VulnJob` |

A sixth built-in, `recordStatsPanel`, exists internally
(`frontend/src/editor/panels/record-stats/`) but is deliberately **not**
exported — it's a purely local computation over the already-loaded record
with no repository dependency, and isn't currently offered as a reusable
building block for embedding hosts.

## Events

| Event | `detail` | Fires when |
| --- | --- | --- |
| `ready` | `[]` | A new record is set up (`mode="create"`) or a record loaded successfully; in edit mode without a `repository` yet, once it's set and the record loaded. Not fired when loading fails — `error` fires instead. |
| `loaded` | `[identifier: string]` (the record key) | A record has been loaded, created, or saved. |
| `deleted` | `[identifier: string]` (the record key) | A record was deleted. |
| `dirtyChange` | `[dirty: boolean]` | The record's unsaved-changes state changed. Also dispatched as `dirty-change`. |
| `error` | `[error: Error]` | An operation against `repository` failed. |

These are Vue custom-element events: `event.detail` is the array of
emitted arguments, so the value itself is `event.detail[0]`.

```js
editor.addEventListener("loaded", (event) => {
  console.info("Loaded:", event.detail[0]);
});

editor.addEventListener("error", (event) => {
  console.error("Vulniverse editor error:", event.detail[0]);
});
```
