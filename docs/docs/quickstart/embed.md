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

A `LoadedRecord` is `{ identifier, vulnerabilityId?, profile, record,
isDraft }`: your key for the record, its CVE/GCVE/OSV ID shown as the
title, its profile, its JSON and whether it's a draft. A
`ValidationResult` is `{ valid, profile, errors }`. The complete page in
step 5 shows both in working code.

The exact shapes, how to report errors (including an invalid record on
save) and all the optional methods for templates, CWE/CPE suggestions,
publishing and Patch2Vuln: [The repository](../embedding/repository.md).

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
        // The ID shown as the title: GCVE, then CVE, then OSV.
        vulnerabilityId:
          record.containers?.cna?.x_gcve
            ?.find((entry) => entry.recordType === "advisory")?.vulnId
          ?? record.cveMetadata?.cveId
          ?? record.id
          ?? null,
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

## 6. Validate on your server

The editor validates as you type, in the browser, but your server should
check every record it stores. `validateRecord` and a rejected save both
expect the same shape (see
[The repository](../embedding/repository.md#loading-and-saving-required)), so one
server function serves both. The official schemas are in this repository:

| Profile | Schema |
| --- | --- |
| `cve-5.2.0` | [`schemas/upstream/cve/5.2.0/CVE_Record_Format_bundled.json`](https://github.com/vulnerability-lookup/Vulniverse/blob/main/schemas/upstream/cve/5.2.0/CVE_Record_Format_bundled.json) |
| `osv-1.9.2` | [`schemas/upstream/osv/1.9.2/schema.json`](https://github.com/vulnerability-lookup/Vulniverse/blob/main/schemas/upstream/osv/1.9.2/schema.json) |
| `gcve-bcp-05-1.7` | The CVE schema for the record, and [`schemas/upstream/gcve/bcp-05/1.7/gcve-bcp-05.schema.json`](https://github.com/vulnerability-lookup/Vulniverse/blob/main/schemas/upstream/gcve/bcp-05/1.7/gcve-bcp-05.schema.json) for each `x_gcve` list in it |

For example in Python, with
[`jsonschema`](https://python-jsonschema.readthedocs.io/):

```python
import json
from jsonschema import Draft7Validator

with open("CVE_Record_Format_bundled.json") as file:
    schema = json.load(file)

# The schema's top level is a choice between a published and a rejected
# record; validating against the whole choice reports a broken record as
# one vague error. Each branch on its own names the actual fields.
published, rejected = schema["oneOf"]
root = {key: value for key, value in schema.items() if key != "oneOf"}
validators = {
    "PUBLISHED": Draft7Validator({**root, **published}),
    "REJECTED": Draft7Validator({**root, **rejected}),
}

def validate(record, profile):
    state = record.get("cveMetadata", {}).get("state")
    validator = validators["REJECTED" if state == "REJECTED" else "PUBLISHED"]
    errors = [
        {
            "path": list(error.absolute_path),
            "schemaPath": list(error.absolute_schema_path),
            "message": error.message,
            "validator": error.validator,
        }
        for error in validator.iter_errors(record)
    ]
    return {"valid": not errors, "profile": profile, "errors": errors}
```

GCVE has a few more rules: it doesn't require the CVE-only fields
`cveMetadata.cveId`, `cveMetadata.assignerOrgId` and
`containers.cna.providerMetadata`, and checks the GCVE extensions. Vulniverse's
own backend implements all of it, in
[`record_validation.py`](https://github.com/vulnerability-lookup/Vulniverse/blob/main/backend/src/vulniverse_api/services/record_validation.py);
use it as the reference, or run the Vulniverse backend next to your
application.

## 7. Listen to events

The element sends these events. The value is in `event.detail[0]`.

| Event | `event.detail[0]` | When |
| --- | --- | --- |
| `loaded` | the record's `identifier` | A record was loaded, created or saved. |
| `deleted` | the record's `identifier` | A record was deleted (only with `deleteRecord` on the repository). |
| `error` | an `Error` | A call to the repository failed. |

There are also `ready` and `dirtyChange`; see
[Events](../embedding/element.md#events).

## 8. Add built-in panels and actions (optional)

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

## In React, Vue or Angular

Set `repository`, `panels` and `actions` like any property of a DOM
element. The order doesn't matter: an editor that has to load a record
waits ("Waiting for a repository…") until `repository` is set, then loads
it. Only the first repository counts; to switch to another one, create a
new element.

**React**: set the properties through a `ref` (this works in React 18 and
19):

```jsx
import { useEffect, useRef } from "react";
import "@nmd03/vulniverse";

export function VulniverseEditor({ repository, recordId, onSaved }) {
  const editor = useRef(null);

  useEffect(() => {
    editor.current.repository = repository;
  }, [repository]);

  useEffect(() => {
    const element = editor.current;
    const loaded = (event) => onSaved?.(event.detail[0]);
    element.addEventListener("loaded", loaded);
    return () => element.removeEventListener("loaded", loaded);
  }, [onSaved]);

  return recordId
    ? <vulniverse-editor ref={editor} mode="edit" record-id={recordId} />
    : <vulniverse-editor ref={editor} mode="create" />;
}
```

**Vue**: tell Vue the tag isn't a Vue component, in `vite.config.ts`:

```js
vue({
  template: {
    compilerOptions: { isCustomElement: (tag) => tag === "vulniverse-editor" },
  },
});
```

```vue
<script setup>
import "@nmd03/vulniverse";
import { repository } from "./repository";
</script>

<template>
  <vulniverse-editor
    :repository="repository"
    mode="edit"
    :record-id="recordId"
    @loaded="(event) => console.log('saved', event.detail[0])"
  />
</template>
```

**Angular**: add `CUSTOM_ELEMENTS_SCHEMA` to the component's `schemas`,
then bind it like any element:

```html
<vulniverse-editor
  [repository]="repository"
  mode="edit"
  [attr.record-id]="recordId"
  (loaded)="onSaved($any($event).detail[0])"
></vulniverse-editor>
```

## Next steps

- [The `<vulniverse-editor>` element](../embedding/element.md): the full
  reference (all repository methods, panels, actions, theming, height).
- [Embedding: Vulnerability-Lookup](../embedding/vl.md): a real
  application that embeds the editor with its own backend.
- [Architecture](../development/architecture.md): how the editor is built
  inside.
