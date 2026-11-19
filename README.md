<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/docs/images/logo-dark.png">
    <img src="docs/docs/images/logo.png" alt="Vulniverse logo" width="400">
  </picture>
</p>


Vulniverse is a web-based editor for authoring, reviewing, and validating
vulnerability records. It supports CVE Record Format 5.2.0, GCVE BCP-05 1.7,
and OSV 1.9.2. Use guided forms to edit a record, navigate it in a collapsible
tree, and inspect the generated JSON.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/docs/images/editor-demo-dark.webp">
    <img src="docs/docs/images/editor-demo-light.webp" width="900"
         alt="Creating a GCVE record in Vulniverse: analysing a patch with Patch2Vuln, reserving a GCVE ID, applying the generated fields, editing a field picked in the tree, previewing the record and publishing it to Vulnerability-Lookup">
  </picture>
</p>

Vulniverse runs as a standalone application with its own backend or as
an embeddable Web Component. It is the vulnerability editor in
[Vulnerability-Lookup](https://github.com/vulnerability-lookup/vulnerability-lookup).

[Try the live demo](https://vulnerability-lookup.github.io/vulniverse/) ·
[Run standalone](#run-standalone) ·
[Embed the editor](#embed-the-editor)

