---
icon: lucide/refresh-cw
---

# Manage schemas

The Editor supports both CVE and GCVE record editing. The relevant schemas are pulled from the official repositories ([CVE](https://github.com/CVEProject/cve-schema) and [GCVE](https://github.com/gcve-eu/bcp-validator)).GCVE is just an extension to the CVE record schema by providing an extra x_gcve extension field which can be populated with additional data. In addition to that there exists extension to the BCP-05 standard defining the GCVE record structure. As of today two extensions exist:

- [**BCP-05-X-01**](https://gcve.eu/bcp/extension/gcve-bcp-05-x-01/): Standard for adding information about AI assisted annotations 

- [**BCP-05-X-02**](https://gcve.eu/bcp/extension/gcve-bcp-05-x-02/): Standrad for using patch2vuln for record creation

!!! info

    Both BCP extension do not have official schemas rather than generic field definitions on the corresponding website. Therefore custom schemas based on these generic field definitions where created in `schema/extensions`. Which extensions are included in the generated GCVE profile is defined in `schema/extensions/gcve/registry.json`.

The `/schema/manifest.json` file contains the definitions of all available profiles which can be used to build the editor UI and their corresponding schema files.

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

The schema files are written to the `schema/upstream` directory.

!!! warning

    Every successful run overwrites the `current Profiles` to point to the version that was just installed.

## UI Schema Creation

The schemas used to display the contents in the frontend are directly generated from the official schemas. They are genereated using the `scripts/generate_editor_schemas.py` script:

```bash
python3 scripts/generate_editor_schemas.py --profile cve-5.2.0 --strict
```
```bash
python3 scripts/generate_editor_schemas.py --profile gcve-bcp-05-1.7 --strict
```

The script will create `schema/generated/<profile>/authorring.schema.json` and `schema/generated/<profile>/ui.schema.json` files.

The layout used in the UI can be configured through the `*.layout.json` files in `schema/editor`.
