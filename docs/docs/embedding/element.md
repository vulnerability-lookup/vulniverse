---
icon: lucide/puzzle
---

# The `<vulniverse-editor>` element

This is the actual integration surface — everything a host application
configures when embedding the editor, whether that host is
[Vulnerability-Lookup](vl.md) or something else entirely.
`config/vulniverse.toml` (see [Configuration](../setup/config.md)) has no
effect here — it's a standalone-app-only concern; a host decides its own
`panels`/`modules` directly, in its own code.

## Steps to embed it

`frontend/src/editor/` has zero host-specific branches anywhere — every
step below lives entirely on the host's side of the
`EditorRepository`/`EditorPanel`/`EditorModule` boundary. See
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
   `repository` (and `panels`/`modules` below) are always assigned as JS
   properties after `createElement` — never as attribute strings, since
   they're objects/arrays, not strings.

5. **(Optional) Add panels and modules** — see [`panels` and
   `modules`](#panels-and-modules) below:
   ```js
   editor.panels = [myCustomPanel, templatesPanel];
   editor.modules = [myCustomModule];
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
| `modules` | `EditorModule[]` | Optional extra header buttons. |
| `panels` | `EditorPanel[]` | Optional extra sidebar tabs — see note below. |

## `repository`

`repository` is a plain object, not a string, so it's always assigned from
JavaScript rather than written as an HTML attribute:

```js
const editor = document.querySelector("vulniverse-editor");
editor.repository = myRepository;
```

It must implement the `EditorRepository` interface
(`frontend/src/editor/contracts.ts`) — `loadRecord`/`createRecord`/
`updateRecord`/`validateRecord`/`deleteRecord` are required;
`getReferenceList`/`listTemplates`+CRUD/`getCnaPublication`+the publish
actions are all optional, and the corresponding UI degrades gracefully
(plain free-text entry, a "not supported here" message) when a given one
is omitted, rather than breaking. See
[Architecture](../development/architecture.md) for the full interface.

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

## `panels` and `modules`

```js
editor.panels = [
  myCustomPanel,  // your own object shaped like EditorPanel
  templatesPanel, // reused straight from Vulniverse's own bundle
];

editor.modules = [
  myCustomModule, // your own object shaped like EditorModule
];
```

`EditorPanel`/`EditorModule` (`frontend/src/editor/contracts.ts`) are just
plain object shapes — nothing requires a panel or module to originate from
Vulniverse, so mixing host-authored and Vulniverse-authored entries in the
same array is expected. There's no config file and no
capabilities-filtering step for an embedded host (that machinery —
`config/vulniverse.toml` + `GET /api/v1/capabilities` — is
standalone-app-only, see [Configuration](../setup/config.md)); a host just
decides the array contents directly in its own code.

`templatesPanel` is a genuine opt-in panel like the others (not a section
baked into the element) — a host has to include it explicitly to get the
Templates UI, the same as `gcveIdentifierPanel`, `cveProgramPanel`, and
`vulnerabilityLookupPanel`. All four are exported from `src/element.ts`, so
a host can import and reuse Vulniverse's own built-in ones instead of
authoring equivalents from scratch — though for
`cveProgramPanel`/`vulnerabilityLookupPanel`/`templatesPanel`
specifically, that only does something useful once the host's own
`EditorRepository` implements the matching optional methods
(`getCnaPublication`/etc., `listTemplates`/etc.).

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
