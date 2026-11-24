# Changelog

All notable changes to Vulniverse. Versions follow
[Semantic Versioning](https://semver.org/): from 1.0.0 on, the editor's
public API (the `<vulniverse-editor>` element, `EditorRepository` and the
exports of the npm package) and the configuration file only change
incompatibly in a new major version.

## [Unreleased]

## [1.0.0] - 2026-11-24

The first stable release, after 0.1.0-alpha.2.

### Upgrading from 0.1.0-alpha.2

1. **Back up the database** before upgrading.
2. **Run the migrations**: `flask --app vulniverse_api db upgrade`
   (with Docker: `docker compose exec backend flask --app vulniverse_api db upgrade`).
   They add organisations, invitations, two-factor authentication and
   session tokens, address records by an internal ID, uppercase the
   `cve`/`gcve` prefix of stored IDs (as Vulnerability-Lookup returned
   them lowercased) and make record IDs unique regardless of case.
3. **If the migrations stop** at `e7a3c1d5b9f2`, two records have IDs that
   differ only in case. Find them, then rename or delete one of each pair
   and run the migrations again:
   ```sql
   SELECT lower(identifier), count(*) FROM vulnerability_record
   GROUP BY lower(identifier) HAVING count(*) > 1;
   ```
4. **Update `config/vulniverse.toml`** if you have one:
    - The download action is now `"download"` (it offers JSON, an HTML
      page and PDF); rename `"download-json"` under `[actions]`.
    - New, optional: `"tutorial"` under `[actions]`; `registration` and
      `two_factor` under `[server]` for multi-user mode.
    - Publishing to Vulnerability-Lookup or the CVE Program now needs the
      servers listed by the operator under `[[panels.vl.instances]]` /
      `[[panels.cve-program.instances]]`; users pick one of them for their
      CNA credentials.
5. **PostgreSQL users**: `DATABASE_URL` must start with
   `postgresql+psycopg://` (the old `.env.example` showed `postgresql://`,
   which doesn't work).

### Added

- **Multi-user mode** is ready for production: accounts, organisations
  with roles, invitation links, open/invite-only/closed registration, and
  optional two-factor authentication (authenticator app) for every
  account. Admins can deactivate accounts and reset passwords or 2FA;
  `create-admin` and `reset-two-factor` CLI commands. Instance admins see
  every organisation's records, with a filter by organisation.
- **OSV 1.9.2** records, alongside CVE 5.2.0 and GCVE BCP-05 1.7, including
  the CVSS calculator and GCVE extensions.
- **Change tracking**: edited fields are marked in the form, closed cards
  say how many fields changed, new entries say "New", removed entries stay
  visible with a Restore button, and a list in the header shows every
  unsaved change with its old and new value, to show or undo one by one.
  Advanced JSON has a line-by-line comparison with the last save.
- **Versions editor** for affected products: single version or range,
  `<` / `≤` upper bounds, status changes within a range, and version-type
  suggestions.
- **Record tree** with search, zoom, missing required fields, and jumping
  to any field in the form.
- **Vulnerability-Lookup / CNA publication**: a timeline of the record's
  state, pulling records and reservations from upstream, a field-by-field
  comparison with the published version, and taking over upstream values.
- **Patch2Vuln**: additional instructions for the analysis, vendor and
  product filled in from the commit URL's owner and repository, and a
  notification when an analysis finishes while the panel is closed.
- **Templates**: export and import single templates as files.
- **Actions**: download as JSON, HTML page or PDF; a guided tutorial.
- Dark mode, a collapsible sidebar, "Expand all" / "Collapse all" and entry
  counts on card lists, and a better layout on small screens.
- Backend validation of CVSS vectors and scores.
- **npm package** of the editor, with TypeScript declarations.
- **For embedders:** the bundle exports `EditorRepositoryError`, so a
  repository can tell the publishing panels about missing CNA credentials
  or a concurrent save, and the editor waits for a `repository` set after
  the element is in the page (as frameworks do) instead of failing.
- Documentation with quick starts for a single user, a team server and
  embedding, published with the demo on GitHub Pages.

### Changed

- Records are addressed by an internal ID, separate from their CVE/GCVE/OSV
  ID; CVE and GCVE IDs are stored with an uppercase prefix.
- GCVE records are validated without the CVE-only required fields that
  the GCVE standard doesn't need.
- The publish action saves the record first and refuses to publish a
  record whose ID doesn't match the reserved one.
- Reloading a saved record that was created in the same session reloads
  it instead of showing an empty record.
- The editor opens a single card on load and keeps several closed.

### Fixed

- Saving and publishing after a concurrent edit no longer overwrites the
  other edit silently.
- Sessions end on password or 2FA reset and on deactivation.
- A Patch2Vuln job started before a new record's first save is no longer
  lost.
- Saving works with a repository that returns the record it was given
  (it failed with a `structuredClone` error).
- When the backend doesn't answer, logging in and saving say so ("is the
  backend running?") instead of showing a `JSON.parse` error, and work
  again once it's back, without reloading the page.
- The Docker setup can read `config/` on systems with SELinux, such as
  Fedora and RHEL.
- Read-only fields look disabled; the record tree jumps to GCVE
  extensions correctly.

## [0.1.0-alpha.4]

A preview of 1.0 for testing, with everything listed under
1.0.0 at the time of its release:

```bash
npm install @nmd03/vulniverse@alpha
```

Upgrading from 0.1.0-alpha.2 works as described under
[Upgrading from 0.1.0-alpha.2](#upgrading-from-010-alpha2).

## [0.1.0-alpha.3]

The first release of the editor on npm. Saving fails with a repository
that returns the record it was given; use 0.1.0-alpha.4.

## [0.1.0-alpha.2] - 2026-11-06

## [0.1.0-alpha.1]

[Unreleased]: https://github.com/vulnerability-lookup/vulniverse/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/vulnerability-lookup/vulniverse/compare/v0.1.0-alpha.2...v1.0.0
[0.1.0-alpha.4]: https://github.com/vulnerability-lookup/vulniverse/compare/v0.1.0-alpha.2...v0.1.0-alpha.4
[0.1.0-alpha.2]: https://github.com/vulnerability-lookup/vulniverse/compare/v0.1.0-alpha.1...v0.1.0-alpha.2
[0.1.0-alpha.1]: https://github.com/vulnerability-lookup/vulniverse/releases/tag/v0.1.0-alpha.1
