# Documentation Style Guide

## Audience

Write for software developers who are unfamiliar with
the internal implementation.

Assume familiarity with common development concepts
but not with project-specific terminology.

## Structure

- Start each document with its purpose.
- Explain prerequisites before procedures.
- Use descriptive headings.
- Keep paragraphs focused.
- Include examples for nontrivial concepts.

## Architecture documentation

When documenting architecture:

1. Explain component responsibilities.
2. Describe how components communicate.
3. Identify important interfaces.
4. Explain data flows.
5. Document architectural trade-offs.
6. Include Mermaid diagrams when helpful.

## API documentation

Document:

- Endpoint or method name
- Purpose
- Input parameters
- Request and response formats
- Error conditions
- Authentication requirements
- Examples

## Configuration documentation

Document:

- Configuration key
- Purpose
- Type
- Default value
- Example
- Relevant restrictions

## Avoid

- Duplicating source code in prose.
- Describing implementation details as public contracts.
- Excessively long introductions.
- Unsupported architectural claims.
- Repeating information from other documentation pages.

