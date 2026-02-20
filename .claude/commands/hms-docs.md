Query official HEC-HMS documentation using the `hms_query_docs` skill.

## When to Use

- Looking up official method parameters (SCS CN, Muskingum Cunge, etc.)
- Understanding HMS file formats from official docs
- Checking version-specific features
- Troubleshooting with USACE-documented error codes

## Usage

Invoke the `hms_doc_query` production agent located at `.claude/agents/hms_doc_query/`.

```
# From this command, query the docs:
Question: <user's question>
Focus area: loss_methods | transform_methods | routing_methods | file_formats | workflows | release_notes | troubleshooting
Version: <optional, e.g., "4.11">
```

## Documentation Sources

| Source | Coverage |
|--------|----------|
| User's Manual | UI workflows, method configuration, how-to guides |
| Technical Reference Manual | Algorithms, equations, parameter definitions |
| Release Notes | Version-specific features and changes |

## Complementary Resources

- **Decompiled source**: Use `hms_investigate_internals` skill for undocumented behavior
- **Hard-won facts**: `.claude/rules/hec-hms/critical-bugs-workarounds.md`
- **File format details**: `.claude/rules/hec-hms/file-formats.md`

## Steps

1. Identify the user's documentation question
2. Determine focus area (loss, transform, routing, file_formats, etc.)
3. Read `.claude/agents/hms_doc_query/AGENT.md` for invocation instructions
4. Query documentation, return answer with source URLs
5. If documentation is insufficient → escalate to `hms_investigate_internals` skill (decompilation)
