# Cross-Repository Coordination (Issue-Driven)

This folder documents the issue-driven coordination pattern for sibling repositories. It should no longer be treated as the primary place to file implementation requests.

## Purpose

When an AI agent needs a feature implemented in a sibling repository as part of current work, the canonical request should be filed as a GitHub issue in the target repository. Local notes here are optional context only.

## Key Principles

1. **Target-Repo Issues Are Canonical** - The feature request belongs in the issue tracker of the repo that should own the work
2. **Human-in-the-Loop Required** - Every cross-repo issue still requires explicit human engagement
3. **Local Notes Are Secondary** - Markdown files here can summarize or link issues, but should not replace them
4. **No Direct AI-to-AI Handoff** - Agents prepare issue-ready context; humans trigger next steps
5. **API Independence** - Python APIs remain completely independent

## Workflow

```
1. Agent identifies immediate implementation need in sibling repo
2. Agent determines which repo should own the feature by generalizability
3. HUMAN opens or confirms a GitHub issue in the target repo using that repo's issue template
4. Local plan/backlog entries record the target issue link
5. Sibling repo implements and tracks progress in the issue / PR flow
6. Original repo integrates/tests against the resolved upstream feature with human oversight
```

## Issue Content Checklist

Each upstream issue should include:

- source repo and workflow that exposed the gap
- why the requested feature belongs in the target repo
- proposed API or behavior
- blocking vs non-blocking status for the downstream repo
- acceptance criteria and any relevant fixture/model references
- links back to the local plan or integration task

## Sibling Repository Locations

| Repository | Local Path | Purpose |
|------------|------------|---------|
| hms-commander | `G:\GH\hms-commander` | HEC-HMS automation |
| ras-commander | `G:\GH\ras-commander` | HEC-RAS automation |
| ras-agent | `G:\GH\ras-agent` | Downstream Illinois integration/application repo |

## HMS-RAS Integration Context

See `../../feature_dev_notes/CROSS_REPO_INTEGRATION_BLUEPRINT.md` for the detailed integration architecture.

## Status Tracking

Track the GitHub issue link in the relevant local plan or backlog entry. If a markdown note is kept here, it should primarily capture the issue URL and integration impact rather than duplicate the full request.

## See Also

- `../../feature_dev_notes/cross-repo/` - Research and future feature exploration
- `../.agent/` - Memory system (STATE, PROGRESS, BACKLOG)
