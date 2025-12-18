# HMS-Commander Backlog

## Ready (No Dependencies)

- [ ] `doc-reorg-001` **Consolidate Documentation** - Reorganize scattered .md files into docs/ structure
- [ ] `doc-reorg-002` **Move Deprecated Files** - Move old/obsolete files to .old directory
- [ ] `agent-infra-001` **Create Agent Framework** - Implement agents/_shared/ with base classes and utilities
- [ ] `agent-infra-002` **HMS Decompile Agent** - Package HMS decompilation workflow as reusable agent
- [ ] `agent-infra-003` **Create Agent Templates** - Templates for AGENT.md, RESULTS_TEMPLATE.md, MODELING_LOG_TEMPLATE.md

## Blocked (Has Dependencies)

- [ ] `code-consolidation-001` **Create Shared Parsing Module** - Consolidate ~200 lines of duplicated parsing logic - Waiting on: agent-infra-001 (framework ready)
- [ ] `code-consolidation-002` **Create Constants Module** - Centralize magic numbers and conversion factors - Waiting on: agent-infra-001
- [ ] `code-consolidation-003` **Update File Operation Classes** - Modify HmsBasin/Met/Control/Gage to use shared parsing - Waiting on: code-consolidation-001
- [ ] `testing-001` **Create Pytest Fixtures** - Fixtures for example projects with cleanup - Waiting on: code-consolidation-003
- [ ] `testing-002` **Unit Tests for Parsing** - >80% coverage for _parsing.py - Waiting on: code-consolidation-001
- [ ] `agent-atlas14-001` **Atlas 14 Precipitation Agent** - Create agent for Region 3 → Atlas 14 update - Waiting on: agent-infra-001
- [ ] `agent-aorc-001` **AORC Gridded Precipitation Agent** - Create agent for AORC configuration - Waiting on: agent-infra-001

## Completed

- [x] `agent-coordination-001` **Initialize Agent Memory System** - Session 1 ✓
- [x] `upgrade-workflow-001` **HMS 3.3→4.11 Upgrade Agent** - A1000000 project, 0.00% deviation ✓

## Project Phases (High-Level)

### Phase 1: Foundation (Current)
- Agent memory and coordination system
- Documentation reorganization
- Agent framework infrastructure

### Phase 2: Code Quality
- Parsing consolidation
- Constants module
- Test coverage improvements

### Phase 3: New Features
- Atlas 14 precipitation agent
- AORC gridded precipitation agent
- Additional HMS version support

## Task Complexity Estimates

| Task ID | Complexity | Estimated Time |
|---------|------------|----------------|
| doc-reorg-001 | Low | 1-2 hours |
| doc-reorg-002 | Low | 1 hour |
| agent-infra-001 | Medium | 3-4 hours |
| agent-infra-002 | Medium | 2-3 hours |
| code-consolidation-001 | High | 4-5 hours |
| testing-001 | Medium | 2-3 hours |
| agent-atlas14-001 | High | 6-8 hours |
