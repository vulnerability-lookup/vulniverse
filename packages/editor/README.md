# Vulniverse editor

The [Vulniverse](https://github.com/vulnerability-lookup/vulniverse)
vulnerability record editor as a single Web Component,
`<vulniverse-editor>`: guided forms for CVE Record Format 5.2.0, GCVE
BCP-05 1.7 and OSV 1.9.2 records, a record tree, preview, change tracking
and validation. Your application provides the storage.

## Install

```bash
npm install @nmd03/vulniverse
```

The package is one ES module with Vue and the styles bundled in; it has
no dependencies.

TypeScript declarations are included, with nothing else to install:
`EditorRepository`, `LoadedRecord`, `ValidationResult` and the other
interfaces type your repository, and
`document.createElement("vulniverse-editor")` returns a typed element.

## Use

Importing the module registers the `<vulniverse-editor>` element. Give
it a *repository*, an object that loads and saves records:

```js
import "@nmd03/vulniverse";

const editor = document.createElement("vulniverse-editor");
editor.setAttribute("mode", "create");          // or "edit" with record-id
editor.setAttribute("profile", "gcve-bcp-05-1.7");

editor.repository = {
  async loadRecord(identifier) { /* → { identifier, profile, record, isDraft } */ },
  async createRecord(record, profile, isDraft) { /* save, return the same shape */ },
  async updateRecord(identifier, record, profile, isDraft) { /* same */ },
  async validateRecord(record, profile) { /* → { valid, profile, errors } */ },
};

document.body.append(editor);
```

`repository`, `panels` and `actions` are JavaScript properties, not HTML
attributes. The editor needs a browser: import it on the client only
(for example not during server-side rendering in Next.js or Nuxt).

## Documentation

- [Embedding quick start](https://vulnerability-lookup.github.io/vulniverse/docs/quickstart/embed/):
  a complete working page, the data shapes, events, built-in panels.
- [The element's full reference](https://vulnerability-lookup.github.io/vulniverse/docs/embedding/element/).
- [Try the editor](https://vulnerability-lookup.github.io/vulniverse/) in your browser.

## License

BSD 2-Clause. See [LICENSE](./LICENSE).
