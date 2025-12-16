# Publishing & Repo Hygiene

This repository is intentionally kept source-focused early on. Large HEC-HMS model datasets, generated outputs, and decompilation artifacts are excluded from git to keep history clean and pushes reliable.

## What Was Done (2025-12-16)

- Restructured `.gitignore` to mirror the organization used in `ras-commander`, tailored for `hms-commander`.
- Stopped tracking and prevented future tracking of:
  - Generated documentation site output (`/site`)
  - Local HMS model/test datasets (e.g., `tests/projects/`, `examples/example_projects/`, `hms_example_projects/`)
  - Decompilation agent artifacts (e.g., `hms_agents/hms_decompiler/`) and development notes (`feature_dev_notes/`)
  - Local agent/task artifacts (`.agent/`, `agent_tasks/`, `.claude/commands/`)
  - Large binary artifacts (`*.dss`, `*.dsc`, `*.zip`, `*.jar`, `*.results`, etc.)
- Rewrote history by creating a new orphan `main` branch and committing only a minimal, publishable set of files.
- Created and pushed a new GitHub repository:
  - `https://github.com/gpt-cmdr/hms-commander`
  - Remote: `origin` = `https://github.com/gpt-cmdr/hms-commander.git`

## Rationale

- GitHub rejects files > 100MB; the repo previously contained tracked large blobs (e.g., a ~130MB zip).
- HMS projects commonly include multi-GB DSS databases and binary outputs that are not appropriate for a source repository.
- Decompilation artifacts are valuable but will be incorporated later as a specialized, separately-managed agent/module.

## How To Add Back Content Later (Deliberately)

- Remove or narrow patterns in `.gitignore` (and/or move datasets to a separate repo or release assets).
- Prefer reproducible download/extraction flows over committing models/binaries.
- If publishing docs, regenerate `/site` via CI and deploy from GitHub Pages rather than committing `site/`.

