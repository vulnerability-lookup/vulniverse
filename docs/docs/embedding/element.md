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
   — CSS inlined, images base64'd, no external dependencies. Copy it into
   the host app's own static assets; there's no publish-to-npm step today.

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
   this is the real integration work. See [`repository`](#repository)
   below.

4. **Construct the element and set it up**:
   ```js
   const editor = document.createElement("vulniverse-editor");

   editor.setAttribute("mode", vulnerabilityId ? "edit" : "create");
   editor.setAttribute("profile", "cve-5.2.0"); // or "gcve-bcp-05-1.7"
   if (vulnerabilityId) editor.setAttribute("record-id", vulnerabilityId);

   editor.repository = new MyRepository({ /* ... */ });
   ```
   `mode`/`profile`/`record-id` are plain HTML attributes (strings only).
   `repository` (and `panels`/`actions` below) are always assigned as JS
   properties after `createElement` — never as attribute strings, since
   they're objects/arrays, not strings.

5. **(Optional) Add panels and actions** — see [`panels` and
   `actions`](#panels-and-actions) below:
   ```js
   editor.panels = [myCustomPanel, templatesPanel];
   editor.actions = [myCustomAction];
   ```

6. **Listen for events** — see [Events](#events) below:
   ```js
   editor.addEventListener("loaded", (e) => { /* e.detail: identifier */ });
   editor.addEventListener("error", (e) => console.error(e.detail));
   ```

7. **Mount it**:
   ```js
   document.getElementById("vulniverse-mount").replaceWith(editor);
   ```

8. **(Optional) Theme it** — the shadow-DOM CSS reads a handful of custom
   properties with fallbacks: `--vulniverse-primary`, `--vulniverse-text`,
   `--vulniverse-background`, `--vulniverse-muted`, `--vulniverse-border`.
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
| `profile` | `string` | Defaults to `"cve-5.2.0"`. |
| `repository` | `EditorRepository` | Set from JavaScript (`editor.repository = ...`), not an HTML attribute — see below. |
| `actions` | `EditorAction[]` | Optional extra header buttons. |
| `panels` | `EditorPanel[]` | Optional extra sidebar tabs — see note below. |

## `repository`

`repository` is a plain object, not a string, so it's always assigned from
JavaScript rather than written as an HTML attribute:

```js
const editor = document.querySelector("vulniverse-editor");
editor.repository = myRepository;
```

It must implement the `EditorRepository` interface
(`frontend/src/editor/contracts.ts`). Four methods are required; the rest
are optional, and the editor degrades gracefully when one is omitted
(a fallback, or a "not supported here" message in the relevant panel)
rather than breaking:

| Method(s) | Required? | If omitted |
| --- | --- | --- |
| `loadRecord`, `createRecord`, `updateRecord`, `validateRecord` | **Required** | — |
| `deleteRecord` | Optional | No delete action in the UI |
| `getReferenceList` | Optional | CWE/CAPEC fields fall back to plain free text |
| `searchCpeVendors`, `searchCpeProducts`, `searchCpes` | Optional | No CPE autocomplete |
| `listTemplates`, `saveTemplate`, `updateTemplate`, `deleteTemplate` | Optional, implement together | Templates panel shows "not supported here" |
| `getCnaPublication`, `reserveCveId`, `publishCna`, `rejectCna`, `abortCna` | Optional, implement together | CVE Program / Vulnerability-Lookup panels show "not supported here" |
| `scoreRecordQuality` | Optional | Record Quality panel shows "not supported here" |
| `submitPatch2VulnJob`, `getPatch2VulnJob` | Optional, implement together | Patch2Vuln panel shows "not supported here" |
| `subscribeJobEvents` | Optional | Patch2Vuln panel falls back to polling instead of live (SSE) updates |

See [Architecture](../development/architecture.md) for the full interface.

`lifecycleTransitions?: LifecycleTransition[]` is a property, not a
method, and its three possible states each mean something different:

| Value | Meaning |
| --- | --- |
| Omitted (`undefined`) | Use the standalone app's own default pair — Publish while a draft, Revert to draft once published (`editor/core/lifecycle.ts`'s `DEFAULT_LIFECYCLE_TRANSITIONS`). |
| Explicit empty array `[]` | This host has no such concept (e.g. Vulnerability-Lookup's CNA API persists immediately, with nowhere to store an incomplete draft) — the editor shows none of these buttons. |
| A custom `LifecycleTransition[]` | The host's own set: `{id, label, targetIsDraft, isVisible?}` each. Unlike `EditorAction`, there's no `run()` — clicking always just calls `controller.save(targetIsDraft)`. |

The standalone app's own `HttpRepository`
(`frontend/src/repositories/HttpRepository.ts`) takes one constructor
argument:

```ts
new HttpRepository(apiRoot = "/api/v1")
```

`apiRoot` is the one genuinely reusable "base URL" setting in the whole
project — change it if Vulniverse's backend is mounted somewhere other than
`/api/v1` relative to the page the editor is embedded on. A host supplying
its *own* `EditorRepository` (as Vulnerability-Lookup does) defines its own
equivalent constructor options instead, talking to whatever backend it
already has; see [Embedding: Vulnerability-Lookup](vl.md).

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

Five built-in panels are exported from `src/element.ts` — none are baked
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
| `ready` | — | The editor has mounted and finished its initial setup. |
| `loaded` | `identifier: string` | A record has been loaded, created, or saved. |
| `deleted` | `identifier: string` | A record was deleted. |
| `dirtyChange` | `dirty: boolean` | The record's unsaved-changes state changed. |
| `error` | `error: Error` | An operation against `repository` failed. |

```js
editor.addEventListener("loaded", (event) => {
  console.info("Loaded:", event.detail);
});

editor.addEventListener("error", (event) => {
  console.error("Vulniverse editor error:", event.detail);
});
```
