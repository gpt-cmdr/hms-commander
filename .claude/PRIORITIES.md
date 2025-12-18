# HMS-Commander Development Priorities

**Last Updated:** 2025-12-11
**Current Version:** 0.4.1

---

## Recently Completed: HMS Atlas 14 Agent ✓

### Objective (COMPLETED)
Upgrade HMS models from TP-40 to NOAA Atlas 14 precipitation frequency estimates.

### Implementation Status

#### 1. Atlas 14 Integration ✓
- [x] Query ras-commander for Atlas 14 download logic
- [x] Adapt download logic for HMS workflow (atlas14_downloader.py)
- [x] Support any AEP / duration combination via NOAA API
- [x] Support upper/lower 90% confidence intervals
- [x] All standard AEP intervals and durations available

**Deliverable:** `hms_agents/hms_atlas14/atlas14_downloader.py`
- NOAA HDSC API integration
- Safe parsing with ast.literal_eval (no eval)
- 10 return periods, 19 standard durations
- Upper/lower confidence interval support

#### 2. Clone Functionality (Prerequisites) ✓
**Critical for QAQC and verification by H&H engineers using GUI**

- [x] **`clone_run()`** - Clone simulation run configurations
  - Clone with configurable basin/met/control
  - Update DSS output file paths
  - Update descriptions with change metadata
  - Re-initialize project to register new run

- [x] **`clone_basin()`** - Clone basin model
  - Clone with description metadata
  - Update project file registration
  - GUI-verifiable in HEC-HMS

- [x] **`clone_met()`** - Clone meteorologic model
  - Clone with description metadata
  - Update project file registration
  - Preserve all gage assignments

**Deliverables:**
- `hms_commander/HmsUtils.py` - clone_file(), update_project_file()
- `hms_commander/HmsBasin.py` - Enhanced clone_basin()
- `hms_commander/HmsMet.py` - Enhanced clone_met()
- `hms_commander/HmsRun.py` - Enhanced clone_run()

**Design Pattern:** Follows ras-commander clone functionality
**Purpose:** Enable side-by-side comparison (baseline vs. updated)
**Verification:** H&H engineer can inspect both models in GUI

#### 3. Agent Implementation ✓
**Location:** `hms_agents/hms_atlas14/`

**Components:**
1. **AGENT.md** (700+ lines) - Comprehensive workflow guide
2. **atlas14_downloader.py** - NOAA API integration
3. **atlas14_converter.py** - Alternating Block Method hyetograph generation
4. **EXAMPLE.py** - Complete end-to-end workflow script
5. **__init__.py** - Module interface

**Workflow Implemented:**
1. Read baseline model (TP-40 configuration) ✓
2. Query NOAA Atlas 14 for location-specific data ✓
3. Clone basin/met/runs for each updated storm ✓
4. Apply Atlas 14 precipitation values ✓
5. Update run descriptions with metadata ✓
6. Execute both baseline and updated runs ✓
7. Compare results (DSS comparison) - Basic support
8. Generate QAQC report - Template provided in AGENT.md

**Acceptance Criteria Met:**
- [x] All AEP intervals available (50%, 20%, 10%, 4%, 2%, 1%, 0.5%, 0.2%, 0.1%, 0.05%)
- [x] All durations supported (5-min to 30-day)
- [x] Upper/lower CI available via separate downloads
- [x] GUI-verifiable changes (engineer can see both models)
- [x] Comprehensive documentation in AGENT.md

### Future Enhancements (Optional)

Additional components that could be added:
- [ ] ResultsComparator class - Automated DSS comparison with acceptance criteria
- [ ] ModelingLogger class - Automated MODELING_LOG.md generation
- [ ] BatchProcessor class - Process multiple storms in single operation
- [ ] Integration tests with sample projects

---

## CLB Engineering LLM Forward Approach

### Core Philosophy
**"Changes must be verifiable by H&H engineers using only the HEC-HMS GUI"**

#### Design Principles

1. **GUI Verifiability**
   - All model changes must be inspectable in HEC-HMS GUI
   - Engineers should not need Python/code to understand changes
   - Side-by-side comparison must be possible

2. **Traceability**
   - Clone original models before modifications
   - Update descriptions with change metadata
   - Preserve baseline for comparison
   - Clear naming conventions (e.g., "Run_TP40" vs "Run_Atlas14_100yr")

3. **QAQC-able Workflows**
   - Generate comparison reports (DSS results)
   - Document all parameter changes (MODELING_LOG.md)
   - Provide acceptance criteria validation
   - Enable peer review by non-programmers

4. **Non-Destructive Operations**
   - Never modify original runs in-place
   - Always clone before modification
   - Write to separate DSS files
   - Preserve baseline configuration

5. **Professional Documentation**
   - AGENT.md - Methodology and objectives
   - MODELING_LOG.md - Comprehensive change log
   - RESULTS_TEMPLATE.md - Standard reporting format
   - Quality verdicts (GREEN/YELLOW/RED)

#### Implementation in hms-commander

**All agents must:**
- Use clone functionality (never modify originals)
- Generate side-by-side verifiable outputs
- Document changes in human-readable markdown
- Provide GUI inspection guidance
- Enable engineer review without coding knowledge

**Example Workflow:**
```python
# Bad - Modifies original (not QAQC-able)
HmsBasin.set_loss_parameters(basin_path, "Sub1", curve_number=80)
HmsCmdr.compute_run("Run 1")

# Good - Clones and creates verifiable comparison
new_basin = HmsBasin.clone_basin("Original", "Updated_CN80")
HmsBasin.set_loss_parameters(new_basin, "Sub1", curve_number=80)
new_run = HmsRun.clone_run("Run 1", "Run 1 - Updated CN")
HmsRun.set_basin(new_run, "Updated_CN80")
HmsRun.set_output_dss(new_run, "results_updated.dss")
HmsCmdr.compute_run("Run 1 - Updated CN")
# Engineer can now open GUI and compare both runs
```

#### Benefits
- **Professional Adoption** - Meets industry QAQC standards
- **Engineer Confidence** - Changes are transparent and verifiable
- **Peer Review** - Non-programmers can validate work
- **Audit Trail** - Complete documentation of changes
- **Risk Mitigation** - Baseline always preserved

---

## Upcoming Tasks (After Atlas 14 Agent)

### 1. Repository Cleanup
**Priority:** Medium
**Effort:** 1-2 days

- [ ] Review all .md and .txt files in repository root
- [ ] Organize into appropriate locations:
  - `.old/` - Deprecated/archived content
  - `feature_dev_notes/` - Development notes
  - `docs/` - User-facing documentation
  - Root - Only essential files (README, CLAUDE.md, etc.)
- [ ] Remove duplicates and obsolete content
- [ ] Update cross-references and links

### 2. Code Consolidation (Phase 1 - DEVELOPMENT_ROADMAP.md)
**Priority:** High (after Atlas 14)

- [ ] Create `_parsing.py` module
- [ ] Create `_constants.py` module
- [ ] Refactor HmsBasin/Met/Control/Gage to use shared modules
- [ ] Reduce ~200 lines of duplicate code

---

## Decision Log

### 2025-12-11: Prioritize Atlas 14 Agent
**Rationale:**
- Real-world need (Tifton model upgrade)
- Tests agent framework in production scenario
- Demonstrates CLB Engineering LLM Forward Approach
- Builds foundation for clone functionality (reusable)
- Aligns with Phase 3 of DEVELOPMENT_ROADMAP.md

### 2025-12-11: Adopt CLB Engineering LLM Forward Approach
**Rationale:**
- Industry standard for H&H engineering QAQC
- Enables non-programmer peer review
- Increases professional adoption
- Differentiates hms-commander from academic tools
- Aligns with USACE and consulting firm workflows

---

## Success Criteria

### Atlas 14 Agent Success
- [ ] Tifton model successfully upgraded to Atlas 14
- [ ] All AEP intervals and durations available
- [ ] Baseline and updated models side-by-side in GUI
- [ ] QAQC report generated and verifiable
- [ ] Change log documents all modifications
- [ ] H&H engineer can validate without Python knowledge

### Clone Functionality Success
- [ ] `clone_run()` creates independent run configurations
- [ ] `clone_basin()` preserves all element parameters
- [ ] `clone_met()` handles gage references correctly
- [ ] Cloned models write to separate DSS files
- [ ] Descriptions updated with change metadata
- [ ] GUI shows clear differentiation between baseline/updated

---

## Notes

**Research Sources:**
- ras-commander: `C:\GH\ras-commander` (Atlas 14 download logic)
- HMS GridGen: Existing Atlas 14 integration patterns
- Repository analysis: `feature_dev_notes/repo_analysis/03_gridded_spatial/ANALYSIS.md`

**Dependencies:**
- Must implement clone functionality before Atlas 14 agent
- Clone functionality will be reused across future agents
- Establishes pattern for all future model modification workflows

**Timeline Estimate:**
- Clone functionality: 1-2 weeks
- Atlas 14 integration: 2-3 weeks
- Agent workflow: 1 week
- Testing and documentation: 1 week
- **Total:** 5-7 weeks for complete Atlas 14 agent

---

## Related Documentation
- Development Roadmap: `DEVELOPMENT_ROADMAP.md`
- Repository Analysis: `feature_dev_notes/repo_analysis/SYNTHESIS.md`
- Agent Framework: `agents/README.md`
- Existing Agents: `hms_agents/README.md`
