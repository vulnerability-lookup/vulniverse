---
icon: lucide/plug
---

# Embed it: the editor in your application

The editor ships as one custom element, `<vulniverse-editor>`, in a single
JavaScript file. Your application gives it a *repository*: a small object
that loads and saves records. Where the records live is up to you.
This page shows the smallest setup that works, then where to go next.

## 1. Get the bundle

From npm, if your application uses a bundler (Vite, webpack, …):

```bash
npm install @nmd03/vulniverse
```

```js
import "@nmd03/vulniverse"; // registers <vulniverse-editor>
```

The package includes TypeScript declarations, with nothing else to
install: type your repository as `EditorRepository`, and
`document.createElement("vulniverse-editor")` returns a typed element.

Or download `vulniverse-editor.js` from the GitHub releases:

| Build | URL |
| --- | --- |
| Latest release | `https://github.com/vulnerability-lookup/Vulniverse/releases/latest/download/vulniverse-editor.js` |
| Nightly (every push to `main`) | `https://github.com/vulnerability-lookup/Vulniverse/releases/download/nightly/vulniverse-editor.js` |

Or build it yourself:

```bash
cd frontend
npm run build:element
# → frontend/dist/element/vulniverse-editor.js (and vulniverse-editor.d.ts)
```

The file is self-contained: CSS and images are inlined. Serve it from your
own site, next to the page that uses it.

## 2. Load it as an ES module

```html
<script type="module">
  import { downloadAction, tutorialAction } from "./vulniverse-editor.js";
</script>
```

Importing the file registers the `<vulniverse-editor>` element. Use a
static `import` at the top of the script, so the element exists before
you create it.

!!! note
    Browsers only load ES modules over HTTP(S), not from `file://`.
    For a quick local test, run `python3 -m http.server` in the folder and
    open `http://localhost:8000/`.

## 3. Create the element

Three plain HTML attributes:

| Attribute | Values |
| --- | --- |
| `mode` | `create` (the default) or `edit` |
| `profile` | `gcve-bcp-05-1.7` (the default), `cve-5.2.0` or `osv-1.9.2`. Used for a new record; a loaded record brings its own. |
| `record-id` | The record's key, required with `mode="edit"` |

`repository`, `panels` and `actions` are objects, so you set them as
JavaScript properties, not attributes.

## 4. Give it a repository

The repository must implement four methods. They all return promises.

| Method | Returns |
| --- | --- |
| `loadRecord(identifier)` | `LoadedRecord` |
| `createRecord(record, profile, isDraft)` | `LoadedRecord` |
| `updateRecord(identifier, record, profile, isDraft)` | `LoadedRecord` |
| `validateRecord(record, profile)` | `ValidationResult` |

A `LoadedRecord` is:

```ts
{
  identifier: string;               // your key for the record, any stable string
  vulnerabilityId?: string | null;  // CVE/GCVE/OSV ID shown as the title; null = none yet
  profile: string;                  // e.g. "gcve-bcp-05-1.7"
  record: object;                   // the record JSON
  isDraft: boolean;
}
```

A `ValidationResult` is:

```ts
{
  valid: boolean;
  profile: string;
  errors: Array<{
    path: Array<string | number>;        // where in the record, e.g. ["containers", "cna", "title"]
    schemaPath: Array<string | number>;
    message: string;
    validator?: string;
    severity?: "error" | "warning";
  }>;
}
```

The editor calls `createRecord` on the first save of a new record and
`updateRecord` after that. If saving fails because the record is invalid,
throw the `RecordValidationError` the bundle exports, with the errors:
the editor then lists them like Validate does. Any other error is shown
as a message and sent as an `error` event.

Everything else on the repository is optional (templates, CVE/CPE
lookups, publishing, Patch2Vuln...). See the
[full list](../embedding/element.md#repository).

## 5. A complete page

This page keeps one record in the browser's `localStorage`. It works as
is: create a record, save it, reload the page, and it comes back. Save the
file as `index.html` next to `vulniverse-editor.js`.

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Vulniverse editor</title>
</head>
<body>
  <div id="vulniverse-mount"></div>

  <script type="module">
    import {
      downloadAction,
      tutorialAction,
    } from "./vulniverse-editor.js";

    const KEY = "vulniverse-record";
    const IDENTIFIER = "local";

    // Store a copy and hand a plain copy back, like a server round-trip.
    function store(record, profile, isDraft) {
      const loaded = {
        identifier: IDENTIFIER,
        vulnerabilityId: record.cveMetadata?.cveId ?? record.id ?? null,
        profile,
        record,
        isDraft,
      };

      localStorage.setItem(KEY, JSON.stringify(loaded));

      return JSON.parse(localStorage.getItem(KEY));
    }

    const repository = {
      async loadRecord(identifier) {
        const saved = JSON.parse(localStorage.getItem(KEY) ?? "null");

        if (!saved || saved.identifier !== identifier) {
          throw new Error(`No record "${identifier}".`);
        }

        return saved;
      },

      async createRecord(record, profile, isDraft) {
        return store(record, profile, isDraft);
      },

      async updateRecord(identifier, record, profile, isDraft) {
        return store(record, profile, isDraft);
      },

      async validateRecord(record, profile) {
        // Replace with a call to your server, returning
        // { valid, profile, errors }.
        throw new Error("Validation is not available here.");
      },
    };

    const editor = document.createElement("vulniverse-editor");

    if (localStorage.getItem(KEY)) {
      editor.setAttribute("mode", "edit");
      editor.setAttribute("record-id", IDENTIFIER);
    } else {
      editor.setAttribute("mode", "create");
      editor.setAttribute("profile", "gcve-bcp-05-1.7");
    }

    editor.repository = repository;
    editor.actions = [downloadAction, tutorialAction];

    editor.addEventListener("loaded", (event) => {
      console.info("Loaded or saved:", event.detail[0]);
    });

    editor.addEventListener("error", (event) => {
      console.error("Editor error:", event.detail[0]);
    });

    document.getElementById("vulniverse-mount").replaceWith(editor);
  </script>
</body>
</html>
```

To store records on your server instead, make each method a `fetch` to
your API and return the same shapes. Validation belongs on the server
too: check the record against the JSON schema of its profile there.

!!! tip
    Without a `lifecycleTransitions` property on the repository, the
    header shows **Publish** and **Revert to draft**, which save with
    `isDraft` set to `false` or `true`. Set `lifecycleTransitions = []`
    if your application has no drafts.

## 6. Listen to events

The element sends these events. The value is in `event.detail[0]`.

| Event | `event.detail[0]` | When |
| --- | --- | --- |
| `loaded` | the record's `identifier` | A record was loaded, created or saved. |
| `deleted` | the record's `identifier` | A record was deleted (only with `deleteRecord` on the repository). |
| `error` | an `Error` | A call to the repository failed. |

There are also `ready` and `dirtyChange`; see
[Events](../embedding/element.md#events).

## 7. Add built-in panels and actions (optional)

The bundle exports ready-made panels and actions. Nothing is added
unless you list it:

```js
import {
  downloadAction,        // Download as JSON, HTML page or PDF
  tutorialAction,        // a short guided tour
  templatesPanel,        // needs listTemplates, saveTemplate, updateTemplate, deleteTemplate
  recordQualityPanel,    // needs scoreRecordQuality
  patch2vulnPanel,       // needs submitPatch2VulnJob, getPatch2VulnJob
  vulnerabilityLookupPanel, // needs getCnaPublication and the publish methods
  cveProgramPanel,       // same, for the CVE Program
} from "./vulniverse-editor.js";

editor.actions = [downloadAction, tutorialAction];
editor.panels = [templatesPanel, recordQualityPanel];
```

A panel whose repository methods are missing still shows, with a
"not supported" message. You can also write your own panels and
actions; they are plain objects.

## Next steps

- [The `<vulniverse-editor>` element](../embedding/element.md): the full
  reference (all repository methods, panels, actions, theming, height).
- [Embedding: Vulnerability-Lookup](../embedding/vl.md): a real
  application that embeds the editor with its own backend.
- [Architecture](../development/architecture.md): how the editor is built
  inside.
