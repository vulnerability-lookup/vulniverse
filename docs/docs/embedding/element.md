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

| Prop | Type | Notes |
| --- | --- | --- |
| `mode` | `"create" \| "edit"` | Defaults to `"create"`. |
| `record-id` | `string` | Required when `mode="edit"`. |
| `profile` | `string` | Defaults to `"cve-5.2.0"`. |
| `repository` | `EditorRepository` | Set from JavaScript (`editor.repository = ...`), not an HTML attribute — see below. |
| `modules` | `EditorModule[]` | Optional extra header buttons. |
| `panels` | `EditorPanel[]` | Optional extra sidebar tabs — see note below. |

`repository` is a plain object, not a string, so it's always assigned from
JavaScript rather than written as an HTML attribute:

```js
const editor = document.querySelector("vulniverse-editor");
editor.repository = myRepository;
```

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
equivalent constructor options instead; see
[Embedding: Vulnerability-Lookup](vl.md).

**Note on `panels`**: `templatesPanel` is a genuine opt-in panel like the
others (not a section baked into the element) — a host has to include it
explicitly to get the Templates UI, the same as `gcveIdentifierPanel`,
`cveProgramPanel`, and `vulnerabilityLookupPanel`. All four are exported
from `src/element.ts`, so a host can import and reuse Vulniverse's own
built-in ones instead of authoring equivalents from scratch — though for
`cveProgramPanel`/`vulnerabilityLookupPanel`/`templatesPanel` specifically,
that only does something useful once the host's own `EditorRepository`
implements the matching optional methods (`getCnaPublication`/etc.,
`listTemplates`/etc.) — see
[Architecture](../development/architecture.md).
