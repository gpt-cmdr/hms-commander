---
name: hms_query_docs
description: |
  Queries official HEC-HMS documentation to answer technical questions. Provides access to
  User's Manual, Technical Reference Manual, Release Notes, and community resources.
  Use when seeking official documentation on HMS methods, parameters, file formats,
  version features, workflow guidance, or troubleshooting error messages.
  Do NOT use for: internal implementation details (use hms_investigate_internals),
  JythonHms API reference (use hms_investigate_internals), or hms-commander API
  questions (read code docstrings directly).
  Trigger keywords: HMS documentation, User's Manual, Technical Reference, loss methods,
  transform methods, routing methods, HMS parameters, file formats, release notes,
  method parameters, official HMS, USACE documentation, error message.
---

# Querying HMS Documentation

## When This Skill Is Activated

You are the HMS documentation query specialist. Route the user's question to the appropriate documentation source.

## Decision Tree

1. **User asks about method parameters** → Query with `focus_area="loss_methods"` / `"transform_methods"` / `"routing_methods"`
2. **User asks about file formats** → Query with `focus_area="file_formats"`
3. **User asks about version features** → Query with `focus_area="release_notes"`
4. **User has an error message** → Query with `focus_area="troubleshooting"`
5. **User wants undocumented internals** → Delegate to `hms_investigate_internals` skill

## Query Workflow

1. Classify the question by focus area:

   | Focus Area | Example Questions |
   |------------|-------------------|
   | `loss_methods` | SCS CN parameters, Green-Ampt infiltration |
   | `transform_methods` | Clark UH parameters, Tc calculation |
   | `routing_methods` | Muskingum-Cunge parameters, Modified Puls |
   | `file_formats` | .basin structure, DSS pathname format |
   | `release_notes` | Features added in HMS 4.11 |
   | `troubleshooting` | WARNING 10020, NullPointerException |

2. Use the production agent's query function:
   ```python
   # Via the production agent at .claude/agents/hms_doc_query/
   query_documentation(question, focus_area="loss_methods", hms_version="4.11")
   ```

3. For parameter details:
   ```python
   get_method_parameters(method_type="loss", method_name="SCS Curve Number")
   ```

4. For release notes:
   ```python
   search_release_notes(query="EAP transform", version="4.11")
   ```

5. Present results to the user, noting any limitations

## Documentation Sources

- **User's Manual**: https://www.hec.usace.army.mil/confluence/hmsdocs/hmsum/latest/
- **Technical Reference**: https://www.hec.usace.army.mil/confluence/hmsdocs/hmstrm/latest/

## Known Limitations

- WebFetch retrieves TEXT only — diagrams and screenshots are referenced but not rendered
- Cannot access local HMS help files or PDF manuals without direct URLs
- Some older documentation may not be on Confluence
- For undocumented features, delegate to `hms_investigate_internals` skill

## If Something Goes Wrong

- **WebFetch timeout**: The USACE Confluence server may be slow — retry once
- **Page not found**: Documentation URL structure may have changed — try the parent page
- **Incomplete answer**: Cross-reference with `hms_investigate_internals` for internal details

## Primary Sources

- `.claude/agents/hms_doc_query/` — Production agent (AGENT.md, doc_query.py)

## Delegation Points

- **Undocumented features** → `hms_investigate_internals` skill
- **Working with basin files** → `hms_parse_basin-models` skill
- **Running simulations** → `hms_execute_runs` skill
