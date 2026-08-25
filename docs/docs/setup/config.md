---
icon: lucide/settings
---

# Configuration

Vulniverse does not currently have an environment-variable or config-file
based settings system. What's configurable today is a short, specific
list, split between the backend, the frontend build, and the embeddable
editor's own props.

## Backend

`backend/src/vulniverse_api/__init__.py`'s `create_app()` hardcodes its
configuration:

```python
app.config.from_mapping(
    SECRET_KEY="development-only-change-me",
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{database_path}",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)
```

- `database_path` is `vulniverse.sqlite` inside Flask's
  [instance folder](https://flask.palletsprojects.com/en/stable/config/#instance-folders)
  (`backend/src/instance/`), which `create_app()` creates automatically.
  There is no setting to point it elsewhere yet.
- `SECRET_KEY` is a literal development placeholder. There is no override
  mechanism today — change the constant in source if you need a different
  value.
- `create_app()` also accepts a `test_config` dict, which is how the test
  suite (`backend/tests/conftest.py`) points `SQLALCHEMY_DATABASE_URI` at
  `sqlite:///:memory:`. This isn't wired up to any runtime entry point
  (`flask run`), only to code that calls `create_app()` directly.

### Which CVE/GCVE schema versions are active

`schemas/manifest.json`'s `currentProfiles` selects which pinned schema
version `scripts/generate_editor_schemas.py` generates from by default
(currently `cve-5.2.0` and `gcve-bcp-05-1.7`). This is a schema-generation-time
setting, not something the running backend or frontend reads — see
[Architecture](../development/architecture.md) for how the generator fits in.

## Frontend dev server

`frontend/vite.config.ts` hardcodes the dev-proxy target:

```ts
server: {
  proxy: {
    "/api": {
      target: "http://127.0.0.1:5000",
      changeOrigin: true,
    },
  },
},
```

If the backend runs on a different host/port during development, this is
the line to change.

## The embeddable `<vulniverse-editor>` element

This is the actual integration surface — everything a host application
configures when embedding the editor:

| Prop | Type | Notes |
| --- | --- | --- |
| `mode` | `"create" \| "edit"` | Defaults to `"create"`. |
| `record-id` | `string` | Required when `mode="edit"`. |
| `profile` | `string` | Defaults to `"cve-5.2.0"`. |
| `repository` | `EditorRepository` | Set from JavaScript (`editor.repository = ...`), not an HTML attribute — see below. |
| `modules` | `EditorModule[]` | Optional extra header buttons. |
| `panels` | `EditorPanel[]` | Optional extra sidebar tabs. |

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
[Embedding: Vulnerability-Lookup](../embedding/vl.md).
