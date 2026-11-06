---
name: review-docs
description: Audit software documentation for accuracy, completeness, and consistency with the repository.
disable-model-invocation: true
---

# Documentation Review

Review the documentation against the actual source code.

## Review process

1. Identify the relevant documentation files.
2. Locate the implementation described by each document.
3. Compare documented behavior against actual behavior.
4. Identify undocumented functionality.
5. Identify obsolete functionality.
6. Check all referenced paths and links.
7. Validate code and configuration examples.
8. Identify unnecessary duplication.

## Classify findings

- Critical: Incorrect instructions that prevent functionality.
- Major: Incorrect or outdated technical information.
- Minor: Missing details or unclear explanations.
- Suggestion: Improvements to structure or readability.

## Output

Produce a review report containing:

- Finding
- Severity
- Documentation location
- Relevant source code location
- Recommended correction

Do not modify documentation unless explicitly requested.

## Execution modes

Determine the execution mode from $ARGUMENTS.

### Default mode: review

When no arguments are provided:

1. Analyze the documentation against the source code.
2. Identify and classify findings.
3. Produce a structured review report.
4. Do not modify files.

### Fix mode

When the argument is `fix`:

1. Review the existing documentation against the source code.
2. Identify all documentation issues.
3. Fix every actionable finding directly.
4. Prioritize Critical and Major findings.
5. Modify documentation files only.
6. Verify each correction against the implementation.
7. Check links, examples, and configuration references.
8. Perform a second review after applying the fixes.
9. Resolve newly discovered issues where possible.
10. Summarize all changes and unresolved findings.

Do not stop after reporting findings.

If a finding cannot be resolved reliably, explain why
rather than inventing missing implementation details.
