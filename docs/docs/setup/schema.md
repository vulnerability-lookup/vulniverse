---
icon: lucide/refresh-cw
---

# Manage schemas

Two scripts, run manually, handle everything about the CVE/GCVE schemas —
neither runs in CI:

1. **`scripts/update_schemas.py`** — fetches and vendors upstream schema
   files from their canonical Git repositories into `schemas/upstream/`,
   and updates `schemas/manifest.json`.
2. **`scripts/generate_editor_schemas.py`** — turns a vendored schema plus
   the hand-maintained layout into the authoring/UI schemas the frontend
   actually uses, per profile.

See [Architecture](../development/architecture.md#schema-tooling-schemas-scripts)
for what each output file is; this page is about the *update* workflow —
pulling in a new upstream version and propagating it through.

## Update to a new CVE Record Format version

```bash
python3 scripts/update_schemas.py \
  --cve-ref v5.3.0 \
  --cve-version 5.3.0
```

- `--cve-ref` is a Git tag, branch, or commit in
  [`CVEProject/cve-schema`](https://github.com/CVEProject/cve-schema)
  (defaults to `v5.2.0` — the version currently vendored).
- `--cve-version` is the version label used for the destination directory
  (`schemas/upstream/cve/<version>/`) and the manifest profile id
  (`cve-<version>`). **It must match the fetched schema's own
  `definitions.dataVersion.default`** — the script actively checks this
  and refuses to install a mismatch, so a typo here fails loudly rather
  than silently vendoring the wrong thing.
- Bundled schemas older than 5.1.x live at a different path inside the
  upstream repo. For 5.0.x, add
  `--cve-source-path schema/v5.0/docs/CVE_JSON_5.0_bundled.json` (the
  script's own `--help` documents this).

The script also verifies the fetched file actually looks like a CVE Record
Format schema (Draft-07, the expected `title`) before installing anything,
and installs atomically — it stages to a temp location and swaps it in, so
a failed run can't leave `schemas/upstream/` half-written.

Add `--dry-run` first if you just want to fetch and verify without
changing anything in the repository.

## Update to a new GCVE BCP-05 version

```bash
python3 scripts/update_schemas.py \
  --gcve-ref <commit-sha> \
  --gcve-version 1.8
```

Same shape as CVE, with one important difference: `--gcve-ref` **defaults
to `main`** on
[`gcve-eu/bcp-validator`](https://github.com/gcve-eu/bcp-validator) — a
moving branch, not a pinned tag. For a reproducible build, pass an exact
commit SHA rather than relying on the default. The script checks the
fetched file's `$id` contains `gcve-bcp-05` and that the serialized schema
mentions `x_gcve`/`vulnId`/`recordType`, as a basic sanity check that the
right file was fetched.

You can update CVE and GCVE in the same invocation by passing both sets of
flags together.

## What changes in `schemas/manifest.json`

Every successful (non-dry-run) call **overwrites `currentProfiles`** to
point at whatever version it just installed:

```json
"currentProfiles": {
  "cve": "cve-5.3.0",
  "gcve": "gcve-bcp-05-1.8"
}
```

Earlier profile entries are *not* deleted from `manifest.json`'s
`profiles` map — only `currentProfiles` moves. If you need to keep
generating editor schemas for an older version too, pass its profile id
explicitly with `--profile` in the next step; anything relying on the
default picks up the new one.

## Regenerate the editor schemas

Updating the vendored schema does not, by itself, change anything the
frontend loads — that requires a regeneration pass, once per affected
profile:

```bash
python3 scripts/generate_editor_schemas.py --profile cve-5.3.0 --strict
python3 scripts/generate_editor_schemas.py --profile gcve-bcp-05-1.8 --strict
```

- Always regenerate **both** profiles after a CVE version bump, even if
  you only asked `update_schemas.py` to update CVE — GCVE's
  `baseSchema` in the manifest points at the *same* CVE schema file, so a
  GCVE profile silently keeps using the old CVE shape until it's
  regenerated too.
- **Use `--strict`.** Without it, a layout path in
  `schemas/editor/cve.layout.json` (or `gcve.layout-extra.json`) that no
  longer exists in the new schema — a field renamed or removed upstream —
  is only printed to stderr as a warning, and generation still succeeds
  with that section silently incomplete. With `--strict`, the same
  situation raises and fails the run, which is what you actually want
  when vetting a version bump.
- Check the printed `generation-report.json` (`schemas/generated/<profile>/`)
  for `missingConfiguredPaths` either way — a `--strict` failure and a
  non-strict warning surface the same information, just with different
  consequences.

If `--strict` fails, the fix is almost always in
`schemas/editor/cve.layout.json`: update or remove the section/field entry
that referenced the path which no longer exists, then run again.

## Review and commit

Regeneration touches two trees:

- `schemas/generated/<profile>/` — `authoring.schema.json`,
  `ui.schema.json`, `fields.json`, `generation-report.json`.
- `frontend/src/generated/schemas/<profile>/` — `authoring.schema.json`,
  `ui.schema.json`, `field-paths.json` (a trimmed projection of
  `fields.json`, generated directly here — see
  [Architecture](../development/architecture.md#schema-tooling-schemas-scripts)).

Diff all of it before committing. `schemas/upstream/` and
`schemas/generated/` are meant to be treated as read-only/generated —
don't hand-edit files inside them, since the next run overwrites whatever
was there.

After committing, restart any running backend dev server. Its schema
validators are cached per profile id for the life of the process
(`lru_cache` in `services/record_validation.py`), so a long-running server
started before the update won't pick up a re-vendored schema published
under the *same* profile id until it's restarted — this only matters if
you re-ran `update_schemas.py` with the same `--cve-version`/
`--gcve-version` to refresh a moving ref like GCVE's `main`, not when
bumping to a genuinely new version number.

Finally, run the backend test suite — `backend/tests/test_record_validation.py`
validates real CVE and GCVE records against whichever schema is currently
vendored, so a version bump that changes required fields or types will
usually show up there first:

```bash
cd backend
uv run pytest tests/test_record_validation.py
```
