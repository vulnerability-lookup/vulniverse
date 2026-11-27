---
icon: lucide/refresh-cw
---

# Manage schemas

The Editor supports CVE, GCVE, OSV and EUVD record editing. The relevant schemas are pulled from the official repositories ([CVE](https://github.com/CVEProject/cve-schema), [GCVE](https://github.com/gcve-eu/bcp-validator) and [OSV](https://github.com/ossf/osv-schema)). GCVE is just an extension to the CVE record schema by providing an extra x_gcve extension field which can be populated with additional data. OSV is a standalone format; its profile (`osv-1.9.2`) reuses the GCVE extension schema for GCVE data stored under `database_specific`. In addition to that there exists extension to the BCP-05 standard defining the GCVE record structure. As of today three extensions exist:

- [**BCP-05-X-01**](https://gcve.eu/bcp/extension/gcve-bcp-05-x-01/): Standard for adding information about AI assisted annotations

- [**BCP-05-X-02**](https://gcve.eu/bcp/extension/gcve-bcp-05-x-02/): Standard for using patch2vuln for record creation

- [**BCP-05-X-03**](https://gcve.eu/bcp/extension/gcve-bcp-05-x-03/): Standard for a vulnerability's handling and disclosure timeline

!!! info

    These BCP extensions do not have official schemas, only generic field definitions on the corresponding website. Therefore custom schemas based on these generic field definitions were created in `schemas/extensions`. Which extensions are included in the generated GCVE profile, and whether each is `published` or still `draft`, is defined in `schemas/extensions/gcve/registry.json`.

The `schemas/manifest.json` file contains the definitions of all available profiles which can be used to build the editor UI and their corresponding schema files. `currentProfiles` names the profile in use for each format (`cve`, `gcve`, `osv`, `euvd`). Each profile entry can define, among other things:

- `kind` (`cve`, `gcve`, `osv` or `euvd`), `label` (the name shown in the UI) and `version`.
- `baseSchema`/`baseProfile` (the upstream schema it builds on, and the profile it extends).
- `extensionSchemas` (additional schemas merged in, e.g. the GCVE extension).
- `schemaOverlay` (a patch applied on top of the base schema).
- `semanticValidator` (a named validator run beyond plain JSON Schema).
- `identifier.strategy` (how the backend reads the record's ID: `cve`, `gcve`, `osv` or `euvd`).
- `validation.notRequired` (dotted paths of fields the base schema requires but the profile doesn't, e.g. `cveMetadata.cveId` for GCVE records; a value that is present is still checked).
- `validation.preferredRootBranch` (which root `oneOf` branch validation errors are reported against when it's unclear which one the record was aiming for, e.g. the published CVE variant).
- an `editor` block controlling how the profile renders in the UI: `layout`, `layoutExtras`, `augmenters`, `variant` (which root `oneOf` variant of the schema the form is built from, e.g. `Published`) and `autoAdditionalPropertiesFrom` (a path whose properties not placed in the layout are still added to the form automatically, e.g. `containers.cna`).

See the `gcve-bcp-05-1.7` entry in `schemas/manifest.json` for a profile using most of these.

The EUVD profile (`euvd-1.0`) has no upstream schema: an EUVD record that ENISA writes for a vulnerability with no CVE is defined by Vulnerability-Lookup, which stores it, and its schema lives in `schemas/euvd/1.0/euvd-record.schema.json`. `scripts/update_schemas.py` leaves it alone.

## Pull Upstream Schema Files

New schema files can be fetched from the official sources using the `scripts/update_schemas.py` script. Every run fetches and installs CVE, GCVE and OSV together; each flag has a default (`--cve-ref v5.2.0`, `--gcve-ref main`, `--osv-ref v1.9.2`), so set all of them:

```bash
python3 scripts/update_schemas.py \
  --cve-ref v5.2.0 --cve-version 5.2.0 \
  --gcve-ref <commit-sha> --gcve-version 1.7 \
  --osv-ref v1.9.2 --osv-version 1.9.2
```

Add `--dry-run` to see what would change without writing anything.

The schema files are written to the `schemas/upstream` directory (`cve`, `gcve` and `osv`).

!!! warning

    Leaving out `--gcve-ref` fetches the moving `main` branch, so pin a commit.

!!! warning

    Every successful run creates or updates the `cve`, `gcve` and `osv` profile entries in `schemas/manifest.json` (missing CVE/GCVE settings get defaults, the OSV entry is rebuilt from defaults merged with the existing one), and overwrites all three `currentProfiles` entries to point to the versions that were just installed.

A new profile also needs its frontend definition in `frontend/src/editor/profiles/` (e.g. `osv-1.9.2.ts`).

## UI Schema Creation

The schemas used to display the contents in the frontend are directly generated from the official schemas. They are generated using the `scripts/generate_editor_schemas.py` script, once per profile:

```bash
python3 scripts/generate_editor_schemas.py --profile cve-5.2.0 --strict
```
```bash
python3 scripts/generate_editor_schemas.py --profile gcve-bcp-05-1.7 --strict
```
```bash
python3 scripts/generate_editor_schemas.py --profile osv-1.9.2 --strict
```
```bash
python3 scripts/generate_editor_schemas.py --profile euvd-1.0 --strict
```

Without `--profile`, the script uses `currentProfiles.cve` from `schemas/manifest.json`.

The script writes three files per profile under `frontend/src/generated/schemas/<profile>/`:

- `authoring.schema.json` — the schema the editor's form validation is built from.
- `ui.schema.json` — the layout/field-ordering schema consumed by the form renderer.
- `field-paths.json` — a flat index of every field path in the profile.

Profiles using the `gcve-extensions` augmenter (GCVE and OSV) also write `frontend/src/generated/gcve/extension-schemas.json`, the bundle of GCVE extension schemas.

Layout paths that don't exist in the schema are printed as warnings; with `--strict` they fail the run, which is useful when a new upstream schema version doesn't translate cleanly.

The layout used in the UI can be configured through the `*.layout.json` files in `schemas/editor`.
