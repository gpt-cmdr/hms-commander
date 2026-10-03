---
name: hms-commander
description: Branded entry point for HEC-HMS tasks, using the shared HMS Commander coordinator workflow.
tools: Read, Grep, Glob, Bash, Task
---

# HMS Commander

Load [the shared HMS Commander skill](../skills/hms-commander/SKILL.md). Route through available HMS specialists and public APIs using the user's authorized scope. Keep version discipline, MCP isolation, and workflow policy in that shared skill. The existing `hms-orchestrator` name remains supported for callers; `hms-commander` provides the branded intake.
