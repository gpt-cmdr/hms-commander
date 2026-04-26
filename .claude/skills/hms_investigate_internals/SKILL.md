---
name: hms_investigate_internals
shared_corpus: true
harness_scope: shared
source_owner: gpt-cmdr
security_review: internal
description: |
  Investigates HEC-HMS internals through decompiled Java classes. Provides JythonHms
  API reference, CLI options, version-specific differences (3.x vs 4.x), and guides
  on-demand decompilation for new discoveries. Use when debugging HMS behavior,
  discovering undocumented features, understanding version differences, validating
  automation approaches, checking JythonHms method signatures, or investigating HMS
  API capabilities. Complements hms_query_docs (official docs) with internal
  implementation details.
  Do NOT use for: official documentation queries (use hms_query_docs), hms-commander
  API questions (read code docstrings), or project file parsing (use hms_parse_basin-models).
  Trigger keywords: decompile, HMS internals, JythonHms API, HMS version differences,
  CLI options, undocumented, HMS jar, debugging HMS, HMS source code, method signatures.
---

# Investigating HMS Internals

## When This Skill Is Activated

You are the HMS internals investigator. Check existing knowledge first before decompiling new classes.

## Decision Tree

1. **User asks about JythonHms API** → Read `hms_agents/hms_decompiler/knowledge/JYTHON_HMS_API.md`
2. **User asks about HMS 3.x support** → Read `hms_agents/hms_decompiler/knowledge/HMS_3x_SUPPORT.md`
3. **User asks about CLI options** → Read `hms_agents/hms_decompiler/knowledge/HMS_CLI_OPTIONS.md`
4. **User needs a new class decompiled** → "On-Demand Decompilation"
5. **Complex investigation** → Delegate to `.claude/agents/hms_decompiler/AGENT.md`

## Quick Answers from Knowledge Base

Before any decompilation, check if the answer already exists:

| Question Pattern | Read This File |
|-----------------|---------------|
| "Does HMS support X method?" | `JYTHON_HMS_API.md` |
| "Does HMS 3.3 support Jython?" | `HMS_3x_SUPPORT.md` (YES, Python 2 required) |
| "How to run HMS without GUI?" | `HMS_CLI_OPTIONS.md` → `HEC-HMS.cmd -lite -script path/to/script.py` |
| "What's the difference between 3.x and 4.x?" | `HMS_3x_SUPPORT.md` + `version-support.md` rule |

All knowledge files are at: `.claude/agents/hms_decompiler/knowledge/`

## On-Demand Decompilation

Only decompile if the knowledge base doesn't have the answer:

1. Locate the HMS jar file (typically `C:\Program Files\HEC\HEC-HMS\4.x\hms.jar`)
2. Run the CFR decompiler:
   ```bash
   cd .claude/agents/hms_decompiler/tools
   java -jar cfr.jar "C:\...\hms.jar" --classfilter "hms.model.ClassName" --outputdir output
   ```
3. Analyze the decompiled Java source
4. If the finding is high-value, document it in the knowledge base
5. Report findings to the user

## Reference Classes Already Available

Pre-decompiled for quick reference:

- **HMS 3.3**: `reference/HMS_3.3/hms/Hms.java`, `hms/model/JythonHms.java`
- **HMS 4.13**: `reference/HMS_4.13/hms/Hms.java`, `hms/model/JythonHms.java`, `hms/command/HmsCommandServerImpl.java`

All at: `.claude/agents/hms_decompiler/reference/`

## Integration with hms-commander

- `HmsJython.py` uses JythonHms API reference for method signatures
- `HmsCmdr.py` uses CLI options for direct Java invocation
- `python2_compatible` flag based on HMS_3x_SUPPORT.md findings
- Error codes and exception patterns from decompiled source

## If Something Goes Wrong

- **CFR not found**: Ensure `tools/cfr.jar` exists in the decompiler agent directory
- **Class not found**: Check class name spelling, use `--classfilter` with partial name
- **Decompilation errors**: Some obfuscated classes may not decompile cleanly — look for alternative classes

## Primary Sources

- `.claude/agents/hms_decompiler/` — Production agent with tools and knowledge
- `.claude/rules/hec-hms/execution.md` — Execution patterns informed by internal findings

## Delegation Points

- **Official docs needed** → `hms_query_docs` skill
- **Version handling needed** → `hms_manage_versions` skill
- **Full investigation** → `.claude/agents/hms_decompiler/AGENT.md`
