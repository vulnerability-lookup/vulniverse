---
icon: lucide/landmark
---

# Architecture

The Vulniverse editor defines an EditorRepository interface in contracts.ts. This interface specifies the contract that repository adapters must implement to connect the editor to the backend of the application in which it is embedded.

A repository adapter acts as the integration layer between Vulniverse and the host application. It translates generic editor operations, such as loading, creating, updating, validating, or deleting vulnerability records, into calls to the host application's own backend API.

![Architecture diagram](../images/architecture-light.svg#only-light)
![Architecture diagram](../images/architecture-dark.svg#only-dark)

Vulniverse provides a set of built-in panels and actions that can be enabled by the embedding application. In the standalone app, which panels/actions/suggestion-lookup features are enabled is controlled by `config/vulniverse.toml` (see [Configuration](../setup/config.md)) and enforced on both sides: the frontend hides what's disabled, and the backend independently rejects requests to a disabled panel's or feature's routes, so a config change is a real restriction, not just a UI preference. Applications can also extend the editor with custom panels and actions and connect them to host-specific functionality through the repository adapter.

This architecture keeps the editor independent of any specific backend implementation while allowing it to integrate with different vulnerability-management platforms.

