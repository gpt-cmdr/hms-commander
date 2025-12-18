# HMS-Commander Learnings

## What Works

### **Decompilation for Undocumented Behavior**
When HMS documentation is unclear or incorrect, decompile the JAR files:
- Extract `hms.jar` from HMS installation
- Use CFR decompiler to convert to Java source
- Search for parameter names in obfuscated classes
- Find exact parameter writing/parsing code

**Example**: Discovered correct parameter is `Index Parameter Type: Index Celerity` (not `Index Method: Celerity`) by decompiling HMS 4.11 Q.java class.

**When to use**: When HMS rejects parameters, produces unexpected behavior, or documentation conflicts with observed behavior.

### **Zero-Value Workarounds for HMS Bugs**
HMS 4.11 treats `0.0` as sentinel value for "missing data" in some contexts:
- Replace `Depth: 0.0` with `Depth: 0.0001` before HMS processes file
- Engineering impact negligible (0.0001 inches = 0.00254 mm)
- Prevents HMS from blanking values during format conversion

**When to use**: When HMS corrupts files during save operations, especially for met model precipitation depths.

### **Comprehensive Change Tracking**
Document every modification with structured format:
```markdown
### [YYYY-MM-DD HH:MM] - [Category] - [Action]
- **File:** [filename]
- **Parameter:** [parameter name]
- **Old Value:** [original value]
- **New Value:** [new value]
- **Justification:** [reason for change]
- **Impact:** [expected impact on results]
```

**Example**: MODELING_LOG.md for A1000000 project documented 11 changes across 10 files with complete justification and impact analysis.

**When to use**: Any agent workflow that modifies model files, especially version upgrades or parameter updates.

### **Quality Verdict System (GREEN/YELLOW/RED)**
Three-level verdict system with acceptance criteria:
- **GREEN**: All criteria passed (peak <1%, volume <0.5%, timing ≤1 timestep)
- **YELLOW**: Minor issues, manual review needed
- **RED**: Critical failures, do not proceed

**Example**: A1000000 upgrade achieved GREEN verdict with 0.00% differences across all criteria.

**When to use**: Any agent workflow that requires validation against baseline results.

### **Session Save/Resume Pattern**
For long-running tasks spanning multiple sessions:
- Save session state to JSON with all context
- Include change log, acceptance criteria, metadata
- Resume with full context restored
- Generate MODELING_LOG.md from session data

**When to use**: Tasks requiring >2 hours, complex multi-step workflows, or workflows requiring user approval checkpoints.

### **Static Method Pattern with @log_call**
Consistent architecture across all HMS file operation classes:
```python
@staticmethod
@log_call
def get_X(file_path: Union[str, Path], name: str) -> Dict[str, Any]:
    """Get configuration for element."""
    # Implementation
```

**When to use**: All new file operation methods (mirrors ras-commander pattern).

### **Encoding Fallback (UTF-8 → Latin-1)**
HMS files from Windows installations often use Latin-1 encoding:
```python
try:
    content = file_path.read_text(encoding='utf-8')
except UnicodeDecodeError:
    logger.debug(f"UTF-8 failed, trying Latin-1")
    content = file_path.read_text(encoding='latin-1')
```

**When to use**: All HMS file read operations.

## What Doesn't Work

### **Manual GUI Intervention**
**Anti-pattern**: "User must open HMS GUI and set parameter manually"

**Why it fails**: Defeats automation purpose, breaks batch workflows, not reproducible.

**What to do instead**: Decompile HMS to find file format, write parameter directly to file, or use Jython scripting.

**Example**: Initially thought `Index Parameter Type` required GUI intervention. Decompilation revealed correct parameter name, enabling direct file editing.

### **Trusting HMS Documentation Alone**
**Anti-pattern**: Assuming HMS documentation is complete and accurate.

**Why it fails**: HMS documentation often lags behind implementation, uses different terminology, or omits critical details.

**What to do instead**: Combine documentation with decompilation, test results, and HMS source code analysis.

**Example**: HMS docs don't mention `Index Parameter Type` parameter at all. Only found via decompilation.

### **Ignoring Pre-Existing Issues**
**Anti-pattern**: Failing agent workflows because of pre-existing project errors.

**Why it fails**: Confuses baseline issues with upgrade-introduced problems, blocks progress on unrelated work.

**What to do instead**: Document pre-existing issues separately in MODELING_LOG.md, exclude from acceptance criteria, provide clear resolution notes (e.g., "Out of scope - pre-existing configuration error").

**Example**: A1000000 project had 2 runs failing in HMS 3.3 due to met model misconfiguration. Documented separately, didn't count as upgrade failures.

### **Making File Read-Only to Prevent HMS Overwrites**
**Anti-pattern**: Setting HMS files to read-only to prevent HMS from rewriting them.

**Why it fails**: HMS requires write permission and throws ERROR 12150 if files are read-only.

**What to do instead**: Pre-process files before HMS opens them (e.g., zero-value workaround), or accept that HMS will rewrite and handle in workflow.

**Example**: Tried making met files read-only to prevent HMS from blanking `Depth: 0.0` values. HMS failed to open project. Solution: Replace 0.0 with 0.0001 before opening.

### **Batching Change Log Updates**
**Anti-pattern**: Making multiple changes and documenting them all at once.

**Why it fails**: Difficult to remember justifications, easy to miss changes, less detailed impact analysis.

**What to do instead**: Log each change immediately after making it with full context.

**Example**: Updated 10 basin files with Index Parameter Type - logged as single change entry (good), not as 10 separate entries (would be redundant).

## Project-Specific Discoveries

### **HMS Version Detection from Path**
HMS version can be reliably detected from installation path:
- HMS 3.x: `C:/Program Files (x86)/HEC/HEC-HMS/3.x` (32-bit)
- HMS 4.x: `C:/Program Files/HEC/HEC-HMS/4.x` (64-bit)
- Java location differs: `java/bin/` (3.x) vs `jre/bin/` (4.x)

**Application**: Auto-detect version to generate appropriate Jython scripts (Python 2 vs 3 syntax).

### **HMS Cross-Section Table Case Sensitivity**
HMS 4.11 is case-sensitive for cross-section table references:
- Basin file: `Cross Section Name: Table 5`
- Pdata file: `TABLE 5` (paired data definition)
- Must match exactly or ERROR 41066: "Could not load cross-section table"

**Application**: When updating basin files, verify case matches pdata definitions.

### **HMS Jython API Differences (3.x vs 4.x)**
HMS 3.x and 4.x use different Jython import paths:
- HMS 3.x: `from hms.model import JythonHms`
- HMS 4.x: Same, but Python 3 syntax required (`print()` not `print ""`)

**Application**: Generate version-appropriate scripts based on HMS installation version.

### **DSS Output Path Resolution**
HMS resolves relative DSS paths from project directory:
- Absolute paths: `C:/Projects/MyProject/results.dss`
- Relative paths: `results.dss` (resolved to project directory)

**Application**: Use absolute paths for cross-project comparisons to avoid ambiguity.

### **Muskingum Cunge Parameter Evolution**
HMS 3.x → 4.x changed required parameters for Muskingum Cunge routing:
- HMS 3.x: `Use Variable Time Step: No` (optional)
- HMS 4.x: `Index Parameter Type: Index Celerity` (REQUIRED) + `Index Celerity: 5` + `Space-Time Method: Automatic DX and DT`

**Application**: Version upgrade agents must add these parameters for all Muskingum Cunge reaches.

## Patterns to Avoid

### **Placeholder Values in Tool Calls**
**Pattern**: Using placeholder values when calling tools with missing parameters.

**Why avoid**: Leads to incorrect results, breaks workflows, wastes compute time.

**What to do instead**: Gather all required parameters before calling tools, or ask user for missing values.

### **Assuming Single-Project Workflow**
**Pattern**: Hardcoding use of global `hms` singleton without `hms_object` parameter support.

**Why avoid**: Limits multi-project capabilities, makes testing harder, reduces code reusability.

**What to do instead**: Accept optional `hms_object` parameter and use `_get_hms_object()` helper.

### **Magic Numbers in Code**
**Pattern**: Hardcoding conversion factors, tolerances, thresholds directly in functions.

**Why avoid**: Unclear origin, hard to maintain, difficult to adjust for different projects.

**What to do instead**: Define constants in `_constants.py` with inline comments explaining source.

## Decision Patterns That Work

### **When in Doubt, Decompile**
If HMS behavior is unclear → Decompile JAR → Find exact implementation → Document discovery

### **Document Pre-existing Issues Separately**
If error exists in baseline → Document in "Pre-Existing Issues" section → Exclude from acceptance criteria

### **Use Evidence for Decisions**
Decision based on: (1) Decompilation results, (2) Test results, (3) HMS docs, (4) Community knowledge - in that order of priority

### **Prefer File Operations Over GUI**
If parameter needed → Search for file format first → Decompile if format unclear → GUI as last resort

## Session-Specific Learnings

### Session 1 (2025-12-10) - Agent Memory System Initialization

**What worked**:
- Simple 5-file memory system is sufficient (don't over-engineer)
- CONSTITUTION.md captures project-specific patterns effectively
- BACKLOG.md task decomposition helps maintain focus

**What to improve**:
- Need clearer decision matrix for documentation reorganization
- Should establish .gitignore patterns early
- Consider user input for ambiguous organizational decisions

**Next session should**:
- Get user confirmation on documentation reorganization strategy
- Execute documentation moves systematically
- Create agent framework infrastructure before tackling code consolidation

### Session (2025-12-17) - Phase 1.5 Development Agents Implementation

**What worked**:
- **Parallel subagent execution**: Launching 2-3 subagents per sprint maximized efficiency
- **Sprint-based implementation**: Breaking Phase 1.5 into 3 sprints made work manageable
- **Reference implementation pattern**: Adapting ras-commander agents provided solid templates
- **Three-tier agent architecture**: Clear separation between subagents, development agents, and production agents

**Key patterns discovered**:
- **Development agents** go in `.claude/agents/` (with optional `reference/` folders)
- **Domain subagents** stay in `.claude/subagents/` (single .md files)
- **Production agents** stay in `hms_agents/` (full folder structure)
- **HMS adaptations**: RasExamples→HmsExamples, rascmdr→hmscmdr, ras_commander→hms_commander

**Parallel subagent implementation pattern**:
```python
# Sprint implementation pattern
# 1. Read ras-commander reference implementations
# 2. Launch 2-3 Task subagents in parallel
# 3. Each subagent creates 2-4 related files
# 4. After completion, update orchestrator routing and INDEX.md
```

**What to improve**:
- Could have launched all 3 sprints simultaneously with more aggressive parallelization
- Should create scripts directory structure before launching subagents

**Next phase should**:
- Implement Phase 2 HMS Domain Infrastructure (Calibration, Jython Engineer)
- Consider using conversation intelligence agents to analyze development patterns
- Run notebook testing infrastructure to validate existing notebooks
