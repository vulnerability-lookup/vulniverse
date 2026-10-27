---
icon: lucide/landmark
---

# Architecture

The Vulniverse editor defines an EditorRepository interface in contracts.ts. This interface specifies the contract that repository adapters must implement to connect the editor to the backend of the application in which it is embedded.

A repository adapter acts as the integration layer between Vulniverse and the host application. It translates generic editor operations, such as loading, creating, updating, validating, or deleting vulnerability records, into calls to the host application's own backend API.

![Architecture diagram](../images/architecture-light.svg#only-light)
![Architecture diagram](../images/architecture-dark.svg#only-dark)

Vulniverse provides a set of built-in panels and actions that can be enabled by the embedding application. Applications can also extend the editor with custom panels and actions and connect them to host-specific functionality through the repository adapter.

This architecture keeps the editor independent of any specific backend implementation while allowing it to integrate with different vulnerability-management platforms.

## Background Jobs

Vulniverse provides a background-job infrastructure for executing long-running operations without blocking the frontend or keeping the initiating HTTP request open.

This infrastructure is currently used by the Patch2Vuln integration, which analyzes patches and generates vulnerability information using an external LLM.
