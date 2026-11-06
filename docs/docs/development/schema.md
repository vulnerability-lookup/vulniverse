---
icon: lucide/refresh-cw
---

# Manage schemas

The Editor supports both CVE and GCVE record editing. The relevant schemas are pulled from the official repositories ([CVE](https://github.com/CVEProject/cve-schema) and [GCVE](https://github.com/gcve-eu/bcp-validator)). GCVE is just an extension to the CVE record schema by providing an extra x_gcve extension field which can be populated with additional data. In addition to that there exists extension to the BCP-05 standard defining the GCVE record structure. As of today three extensions exist:

- [**BCP-05-X-01**](https://gcve.eu/bcp/extension/gcve-bcp-05-x-01/): Standard for adding information about AI assisted annotations

- [**BCP-05-X-02**](https://gcve.eu/bcp/extension/gcve-bcp-05-x-02/): Standard for using patch2vuln for record creation

- [**BCP-05-X-03**](https://gcve.eu/bcp/extension/gcve-bcp-05-x-03/): Standard for a vulnerability's handling and disclosure timeline

!!! info

    These BCP extensions do not have official schemas, rather than generic field definitions on the corresponding website. Therefore custom schemas based on these generic field definitions were created in `schemas/extensions`. Which extensions are included in the generated GCVE profile, and whether each is `published` or still `draft`, is defined in `schemas/extensions/gcve/registry.json`.

The `schemas/manifest.json` file contains the definitions of all available profiles which can be used to build the editor UI and their corresponding schema files. Each profile entry can define, among other things: `baseSchema`/`baseProfile` (the upstream schema it builds on, and the profile it extends), `extensionSchemas` (additional schemas merged in, e.g. the GCVE extension), `schemaOverlay` (a patch applied on top of the base schema), `semanticValidator` (a named validator run beyond plain JSON Schema), and an `editor` block (`layout`, `layoutExtras`, `augmenters`) controlling how the profile renders in the UI. See the `gcve-bcp-05-1.7` entry in `schemas/manifest.json` for a profile using all of these.

## Pull Upstream Schema Files

New schema files can be fetched from the official sources using the `scripts/update_schemas.py` script:

```bash
python3 scripts/update_schemas.py \
  --cve-ref v5.2.0 \
  --cve-version 5.2.0
```
```bash
python3 scripts/update_schemas.py \
  --gcve-ref <commit-sha> \
  --gcve-version 1.7
```

The schema files are written to the `schemas/upstream` directory.

!!! warning

    Every successful run overwrites the `currentProfiles` entry in `schemas/manifest.json` to point to the version that was just installed.

## UI Schema Creation

The schemas used to display the contents in the frontend are directly generated from the official schemas. They are generated using the `scripts/generate_editor_schemas.py` script:

```bash
python3 scripts/generate_editor_schemas.py --profile cve-5.2.0 --strict
```
```bash
python3 scripts/generate_editor_schemas.py --profile gcve-bcp-05-1.7 --strict
```

The script writes four files per profile under `schemas/generated/<profile>/`:

- `authoring.schema.json` — the schema the editor's form validation is built from.
- `ui.schema.json` — the layout/field-ordering schema consumed by the form renderer.
- `fields.json` — a flat index of every field path in the profile.
- `generation-report.json` — a report of what the generator did (e.g. fields it couldn't map automatically), useful when a new upstream schema version doesn't translate cleanly.

The layout used in the UI can be configured through the `*.layout.json` files in `schemas/editor`.
