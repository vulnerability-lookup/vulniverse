<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/docs/images/logo-dark.png">
    <img src="docs/docs/images/logo.png" alt="Vulniverse logo" width="400">
  </picture>
</p>

<p align="center">
  <a href="https://vulnerability-lookup.github.io/vulniverse/"><img alt="Live demo" src="https://img.shields.io/badge/demo-try%20it-blue"></a>
  <a href="https://github.com/vulnerability-lookup/Vulniverse/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/vulnerability-lookup/Vulniverse/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/vulnerability-lookup/Vulniverse/releases"><img alt="Release" src="https://img.shields.io/github/v/release/vulnerability-lookup/Vulniverse?include_prereleases&sort=semver&filter=v*&label=release"></a>
  <a href="LICENSE"><img alt="License: BSD 2-Clause" src="https://img.shields.io/badge/license-BSD%202--Clause-blue"></a>
</p>


Vulniverse is a web editor for vulnerability records in **CVE Record Format
5.2.0**, **GCVE BCP-05 1.7** and **OSV 1.9.2**. Guided forms know the
schema, so you describe the vulnerability and Vulniverse gets the
structure right: version ranges, CVSS scores, CWE and CAPEC references,
credits and all the rest. It's the vulnerability editor of
[Vulnerability-Lookup](https://github.com/vulnerability-lookup/vulnerability-lookup).

<p align="center">
  <a href="https://vulnerability-lookup.github.io/vulniverse/"><b>Try it in your browser</b></a> (no installation, no account) ·
  <a href="https://vulnerability-lookup.github.io/vulniverse/docs/quickstart/single-user/">Run it yourself</a> ·
  <a href="https://vulnerability-lookup.github.io/vulniverse/docs/quickstart/embed/">Embed it in your app</a>
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/docs/images/editor-demo-dark.webp">
    <img src="docs/docs/images/editor-demo-light.webp" width="900"
         alt="Creating a GCVE record in Vulniverse: analysing a patch with Patch2Vuln, reserving a GCVE ID, applying the generated fields, editing a field picked in the tree, previewing the record and publishing it to Vulnerability-Lookup">
  </picture>
</p>

<p align="center"><i>From a patch to a published GCVE record: draft it with Patch2Vuln, check it, publish it to Vulnerability-Lookup.</i></p>

## One record, every view you need

<table>
  <tr>
    <td width="50%" valign="top">
      <h4>Forms that know the schema</h4>
      <p>Every field of the record, laid out the way you think about it. Version ranges read like a sentence, version types are suggested as you type, and a calculator builds the CVSS vector.</p>
      <picture>
        <source media="(prefers-color-scheme: dark)" srcset="docs/docs/images/screenshots/editor-dark.webp">
        <img src="docs/docs/images/screenshots/editor-light.webp" alt="The form for an affected product's versions: a range from 0 below 4.1.0, compared as semver">
      </picture>
    </td>
    <td width="50%" valign="top">
      <h4>The whole record at a glance</h4>
      <p>A tree of everything in the record, with what's required, missing or changed. Search names and values, then jump straight to the field in the form.</p>
      <picture>
        <source media="(prefers-color-scheme: dark)" srcset="docs/docs/images/screenshots/tree-dark.webp">
        <img src="docs/docs/images/screenshots/tree-light.webp" alt="The record tree: the record's containers, lists and values as a graph">
      </picture>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <h4>See it as your readers will</h4>
      <p>A rendered preview of the record (description, affected versions, severity, references) before anyone else does.</p>
      <picture>
        <source media="(prefers-color-scheme: dark)" srcset="docs/docs/images/screenshots/preview-dark.webp">
        <img src="docs/docs/images/screenshots/preview-light.webp" alt="The preview: the published record's metadata, description and solution">
      </picture>
    </td>
    <td width="50%" valign="top">
      <h4>Every change in sight</h4>
      <p>Edits are marked in the form and listed in one place with the old and new value. Undo a single change, or restore an entry you removed.</p>
      <picture>
        <source media="(prefers-color-scheme: dark)" srcset="docs/docs/images/screenshots/changes-dark.webp">
        <img src="docs/docs/images/screenshots/changes-light.webp" alt="The list of unsaved changes: a reworded title and a removed problem type, each with Show and Undo">
      </picture>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <h4>The JSON, when you want it</h4>
      <p>Edit the raw record directly, or compare it line by line with the last save before you commit to it.</p>
      <picture>
        <source media="(prefers-color-scheme: dark)" srcset="docs/docs/images/screenshots/json-changes-dark.webp">
        <img src="docs/docs/images/screenshots/json-changes-light.webp" alt="The JSON comparison: removed lines in red, added lines in blue">
      </picture>
    </td>
    <td width="50%" valign="top">
      <h4>Know it's complete</h4>
      <p>A quality score shows what a reader would miss (scope, severity, what to do about it) before a reviewer has to point it out.</p>
      <picture>
        <source media="(prefers-color-scheme: dark)" srcset="docs/docs/images/screenshots/quality-dark.webp">
        <img src="docs/docs/images/screenshots/quality-light.webp" alt="The record quality check: a score of 100 out of 100, by category">
      </picture>
    </td>
  </tr>
</table>

## Why Vulniverse

- **Start from the fix.** Point Patch2Vuln at a commit and it drafts the
  record for you: description, affected files, weakness and severity, for
  you to review and apply field by field.
- **Publish where it counts.** Reserve GCVE IDs and publish to
  Vulnerability-Lookup, or to the CVE Program as a CNA, from the same
  screen you write in.
- **Never start from a blank page.** Templates fill in what your records
  have in common: your vendor, your references, your boilerplate.
- **Made for teams.** Organisations, roles, invitations and two-factor
  authentication.
- **Fits into your tools.** The editor is also a single Web Component,
  `<vulniverse-editor>`, which you can drop into your own application with
  your own storage behind it.

## Get started

| | |
|---|---|
| **Try it now** | The [live demo](https://vulnerability-lookup.github.io/vulniverse/) runs entirely in your browser. |
| **Run it yourself** | Follow the quick start [for yourself](https://vulnerability-lookup.github.io/vulniverse/docs/quickstart/single-user/) or [for your team](https://vulnerability-lookup.github.io/vulniverse/docs/quickstart/team/), or [build it from source](https://vulnerability-lookup.github.io/vulniverse/docs/development/from-source/). |
| **Embed it** | Add [`<vulniverse-editor>`](https://vulnerability-lookup.github.io/vulniverse/docs/quickstart/embed/) to your application, as [Vulnerability-Lookup does](https://vulnerability-lookup.github.io/vulniverse/docs/embedding/vl/). |

Configuration, production setup and the architecture are described in the
[documentation](https://vulnerability-lookup.github.io/vulniverse/docs/).

## License

Vulniverse is released under the [BSD 2-Clause License](LICENSE).
