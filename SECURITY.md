# Security policy

## Supported versions

Security fixes go into the latest release. Please upgrade to it before
reporting, and check the [changelog](CHANGELOG.md) for fixes that are
already released.

| Version | Supported |
| --- | --- |
| Latest 1.x release | Yes |
| 0.1.0 alphas | No, please upgrade |

## Reporting a vulnerability

Please **don't open a public issue** for a security problem.

Report it privately through GitHub: on the repository's
[Security tab](https://github.com/vulnerability-lookup/Vulniverse/security),
choose **Report a vulnerability**. Only you and the maintainers see the
report.

Helpful to include:

- the affected version, and whether it's the standalone app (local or
  multi-user mode) or the embedded `<vulniverse-editor>`;
- steps to reproduce, or a proof of concept;
- what an attacker could do with it.

We'll confirm the report, keep you updated on the fix, and credit you in
the advisory and the changelog unless you'd rather stay anonymous.

## Scope

In scope: this repository's backend, the editor (standalone and as the
npm package `@nmd03/vulniverse`), and the deployment templates in
`backend/deploy/`.

Out of scope: problems in Vulnerability-Lookup, the CVE Program's
services or a Patch2Vuln service themselves (please report those to their
projects), and setups that ignore the
[production guide](https://vulnerability-lookup.github.io/vulniverse/docs/setup/production/),
for example running without TLS.
