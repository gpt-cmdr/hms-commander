---
name: api-consistency-auditor
description: Audit hms-commander public Python API changes against the repository's verified conventions (static namespace classes, @staticmethod then @log_call, hms_object=None project context, parameter vocabulary, Union[str, Path] path inputs, return annotations, Google-style docstrings, __all__ exports, compatibility aliases). Use for PR review, feature-request criteria, and baseline audits of hms_commander code. Report-only; it does not edit code, execute HEC-HMS, or approve merges.
shared_corpus: true
harness_scope: shared
source_owner: gpt-cmdr
security_review: internal
---

# API Consistency Auditor

Check that new or changed `hms_commander` public APIs follow the conventions the library already uses. The rules, their evidence, and the current baseline are in [the API rules](references/api-rules.md). Intentional exceptions are recorded in the repository `.auditor.yaml`. Read both before an audit.

## Workflow

1. Read the root `AGENTS.md`, `hms_commander/AGENTS.md`, and the relevant sections of `STYLE_GUIDE.md` and `CONTRIBUTING.md`.
2. Define the scope: a diff or PR (default), named modules, or the whole package. For a diff, identify added and changed public classes and methods.
3. Run the stdlib-only checker from the repository root. It parses source with `ast`; it does not import the package or run HEC-HMS.

   ```bash
   python .claude/skills/api-consistency-auditor/scripts/check_api_consistency.py [paths...] [--format json] [--fail-on major]
   ```

4. Review what the checker cannot decide: parameter vocabulary (HMS-API-06), return-type meaning (HMS-API-08), `hms_commander/schemas.py` updates for DataFrame column changes (HMS-API-10), and compatibility aliases for renamed APIs (HMS-API-11).
5. Classify each finding. In a PR review, report findings on new or changed code as required changes and pre-existing baseline gaps separately as context. A checker hit is evidence to evaluate; confirm it against the source before reporting it as a defect.
6. Propose an `.auditor.yaml` exception only with a specific architectural reason. Exceptions are maintainer decisions.

## Boundaries

- Applies to repository-maintained `hms_commander` code and intended contributions. It does not govern users' own scripts, notebooks, or projects that call the library.
- Report by default. Edit code only when the user authorizes a fix, and keep fixes within the requested scope.
- Do not import ras-commander-only rules (HDF `@standardize_input` file types, `plan_number`, `ras_object`, worker and callback classes). HMS-RAS handoff conventions are covered by the `hms-ras-integration` skill.
- Docstring prose quality belongs to the shared [Technical Writing Auditor](../technical-writing-auditor/SKILL.md); this skill checks docstring presence and format only.

## Report

For each finding give the rule ID, severity, `path:line`, symbol, the observed pattern, the expected pattern, and whether it is new in the reviewed change or baseline. End with counts by rule, the files covered, exceptions applied from `.auditor.yaml`, and a disposition for the reviewed scope: `pass`, `pass with suggestions`, `needs revision` (any major finding, or a minor finding on new or changed public API), or `incomplete`. An API consistency pass does not establish functional correctness, hydrologic validity, or merge approval.
