# Cognitive Architecture

**Purpose**: Explain HMS Commander's hierarchical knowledge organization, progressive disclosure, and agent orchestration patterns.

---

## Overview

HMS Commander uses a sophisticated cognitive architecture that organizes knowledge hierarchically and enables progressive disclosure of context. This approach allows AI assistants to efficiently navigate from high-level concepts to detailed implementation patterns.

---

## Hierarchical Knowledge Structure

```mermaid
graph TB
    subgraph "Shared Contract"
        A[AGENTS.md<br/>Shared Source of Truth]
    end

    subgraph "Harness Adapters"
        B[CLAUDE.md<br/>Claude Loader]
        C[.agents/skills/<br/>Generated Codex Bridge]
        D[.codex/<br/>Codex Config]
    end

    subgraph "Claude-Native Framework"
        E[.claude/MANIFEST.md<br/>Component Registry]
        F[.claude/INDEX.md<br/>Navigation Index]
        G[.claude/rules/]
        H[.claude/skills/]
        I[.claude/agents/]
        J[.claude/commands/]
    end

    subgraph "Folder-Based Claude Agents"
        K[.claude/agents/<br/>Tooling folders]
        L[agent_tasks/<br/>Task Templates]
    end

    A --> B
    A --> C
    A --> D
    B --> E
    B --> F
    E --> G
    E --> H
    E --> I
    E --> J
    H --> K
    I --> K
    J --> L

    style A fill:#ffcccc
    style B fill:#ffe6cc
    style C fill:#ffe6cc
    style D fill:#ffe6cc
    style G fill:#e1f5ff
    style H fill:#fff4e1
    style I fill:#fff4e1
    style K fill:#e7f5e7
```

---

## Progressive Disclosure Pattern

Claude uses **@imports** to enter the shared contract and progressively disclose Claude-native context:

```mermaid
flowchart LR
    A[User asks:<br/>'How do clone workflows work?'] --> B{Claude reads<br/>CLAUDE.md}

    B --> C[@import AGENTS.md]
    C --> D[Use .claude/MANIFEST.md<br/>for Claude-native discovery]
    D --> E[Read .claude/rules/hec-hms/clone-workflows.md]

    E --> F[Detailed Pattern:<br/>- Non-destructive clones<br/>- GUI verification<br/>- QAQC workflows]

    F --> G[Related Context:<br/>execution.md<br/>basin-files.md]

    G --> H[Claude has full context<br/>to answer question]

    style A fill:#e1f5ff
    style C fill:#ffcccc
    style E fill:#fff4e1
    style H fill:#e7f5e7
```

**Key Principle**: Context is loaded **on-demand** based on user's question, not all at once.

---

## Cognitive Flow: Request to Execution

```mermaid
sequenceDiagram
    participant User
    participant Claude
    participant Command as Slash Command
    participant Task as Task Library
    participant Skill
    participant Subagent
    participant Code as HMS Commander API

    User->>Claude: "Run HMS simulation with updated precipitation"

    Claude->>Claude: Read CLAUDE.md and AGENTS.md<br/>Identify workflow type

    Claude->>Command: /hms-run
    Note over Command: Slash command expands prompt

    Command->>Claude: Execute workflow:<br/>1. Initialize project<br/>2. Update met model<br/>3. Run simulation

    Claude->>Task: Read agent_tasks/tasks/<br/>020-run-simulation.md
    Note over Task: Task template provides structure

    Task->>Skill: Activate skill:<br/>hms_execute_runs
    Note over Skill: Skill knows HMS execution patterns

    Skill->>Subagent: Delegate to:<br/>run-manager-specialist
    Note over Subagent: Subagent has domain expertise

    Subagent->>Code: HmsCmdr.compute_run("Run 1")
    Code->>Code: Generate Jython script
    Code->>Code: Execute HEC-HMS
    Code-->>User: Simulation complete ✓
```

**Layers Explained**:
1. **Slash Command**: User-friendly entry point
2. **Task Library**: Reusable workflow templates
3. **Skill**: Task-specific knowledge
4. **Subagent**: Domain specialist
5. **Code**: Static class API execution

---

## Agent Orchestration Architecture

```mermaid
graph TB
    subgraph "User Layer"
        A[User Request]
    end

    subgraph "Orchestration Layer"
        B[HMS Orchestrator<br/>Subagent]
    end

    subgraph "Specialist Subagents"
        C1[basin-model-specialist]
        C2[met-model-specialist]
        C3[run-manager-specialist]
        C4[calibration-analyst]
    end

    subgraph "Foundation Agents"
        D1[hms_decompiler<br/>Code Archaeologist]
        D2[hms_doc_query<br/>Documentation Agent]
    end

    subgraph "Skills Layer"
        E1[hms_execute_runs]
        E2[hms_parse_basin-models]
        E3[hms_update_met-models]
        E4[hms_investigate_internals]
        E5[hms_query_docs]
    end

    subgraph "API Layer"
        F[HMS Commander<br/>Static Classes]
    end

    A --> B
    B --> C1
    B --> C2
    B --> C3
    B --> C4

    C1 --> E2
    C2 --> E3
    C3 --> E1

    E4 --> D1
    E5 --> D2

    E1 --> F
    E2 --> F
    E3 --> F
    D1 --> F
    D2 --> F

    style B fill:#ffcccc
    style C1 fill:#e1f5ff
    style C2 fill:#e1f5ff
    style C3 fill:#e1f5ff
    style C4 fill:#e1f5ff
    style E1 fill:#fff4e1
    style F fill:#e7f5e7
```

**Routing Logic**:
- **Orchestrator** classifies request → routes to specialist
- **Specialist** uses domain knowledge → activates skill
- **Skill** executes workflow → calls API
- **API** performs operation → returns result

---

## Three-Tier Agent Architecture

```mermaid
graph LR
    subgraph "Tier 1: Specialist Subagents"
        A1[.claude/agents/<br/>Single .md files]
        A2[Purpose: Domain experts<br/>using HMS Commander API]
        A3[Examples:<br/>basin-model-specialist<br/>met-model-specialist]
    end

    subgraph "Tier 2: Development Agents"
        B1[.claude/agents/<br/>.md + optional reference/]
        B2[Purpose: Dev infrastructure<br/>notebooks, docs, testing]
        B3[Examples:<br/>documentation-generator<br/>notebook-runner]
    end

    subgraph "Tier 3: Folder-Based Claude Agents"
        C1[.claude/agents/&lt;name&gt;/<br/>Folders with tools/]
        C2[Purpose: Complete Claude-native automation<br/>self-contained workflows]
        C3[Examples:<br/>hms_decompiler/<br/>hms_atlas14/]
    end

    A1 --> A2 --> A3
    B1 --> B2 --> B3
    C1 --> C2 --> C3

    style A1 fill:#e1f5ff
    style B1 fill:#fff4e1
    style C1 fill:#e7f5e7
```

**Why Three Tiers?**:
- **Tier 1**: Lightweight, framework-integrated
- **Tier 2**: Development tools, not for end users
- **Tier 3**: Shareable, production-ready, standalone

---

## Task Template System (Cognitive Backbone)

```mermaid
graph TB
    subgraph "User Request"
        A[Task: Run simulation<br/>with calibrated parameters]
    end

    subgraph "Task Template"
        B[agent_tasks/tasks/<br/>020-run-simulation.md]
        C[Context Files:<br/>@project.hms<br/>@model.basin]
        D[Constraints:<br/>- Verify parameters<br/>- Check DSS output]
        E[Acceptance Criteria:<br/>- Simulation completes<br/>- Results DSS exists]
    end

    subgraph "Execution"
        F[Load Context]
        G[Apply Constraints]
        H[Execute Workflow]
        I[Verify Acceptance]
    end

    subgraph "Artifact"
        J[agent_tasks/runs/<br/>YYYYMMDD_HHMMSS/]
        K[TASK.md<br/>Log of execution]
        L[results.dss<br/>Output artifacts]
    end

    A --> B
    B --> C
    B --> D
    B --> E

    C --> F
    D --> G
    E --> I

    F --> H
    G --> H
    H --> I

    I --> J
    J --> K
    J --> L

    style B fill:#ffcccc
    style H fill:#fff4e1
    style J fill:#e7f5e7
```

**Task Template Benefits**:
- **Repeatability**: Same structure every time
- **Context**: Automatic file loading
- **Safety**: Constraints prevent errors
- **Verification**: Acceptance criteria validate success
- **Audit Trail**: Runs folder preserves history

---

## Progressive Disclosure Example

### Level 1: Shared Contract (`AGENTS.md`)
```
User: "How do I execute HMS simulations?"

Agent reads: AGENTS.md
├── Shared harness contract
├── HMS working rules
└── Navigation to scoped AGENTS.md files
```

### Level 2: Claude Loader (`CLAUDE.md`)
```
Claude loads: CLAUDE.md
├── @AGENTS.md
├── Claude adapter notes
└── Pointer to .claude/MANIFEST.md
```

### Level 3: Claude-Native Pattern Details
```
Claude reads: .claude/rules/hec-hms/execution.md
├── HmsCmdr patterns
├── HmsJython script generation
├── Version detection (HMS 3.x vs 4.x)
├── Parallel execution patterns
└── Related patterns: @import basin-files.md
```

### Level 4: Code Execution
```
Claude has full context:
- Knows HmsCmdr.compute_run() is the method
- Knows to use init_hms_project() first
- Knows version detection is automatic
- Executes code with confidence
```

---

## Knowledge Organization Principles

### 1. **Single Source of Truth**
- Shared rules live in `AGENTS.md`
- Claude-specific files reference shared rules instead of copying them
- Generated Codex bridge entries are links, not duplicate skill source

### 2. **Hierarchical Loading**
- Start general → progress to specific
- Load only what's needed for task
- Efficient context usage

### 3. **Cross-Referencing**
- Related patterns link bidirectionally
- Skills reference rules
- Subagents reference skills
- Complete knowledge graph

### 4. **Self-Documenting**
- Structure mirrors architecture
- File locations indicate purpose
- Naming conventions convey meaning

---

## Cognitive Layers Summary

| Layer | Location | Purpose | Loaded When |
|-------|----------|---------|-------------|
| **Shared Contract** | `AGENTS.md` | Cross-harness source of truth | Always |
| **Claude Loader** | `CLAUDE.md` | Imports `AGENTS.md` and adds Claude notes | Claude sessions |
| **Codex Bridge** | `.agents/skills/` | Generated skill links | Codex skill discovery |
| **Patterns** | `.claude/rules/*/` | Claude preload helpers and detailed notes | When specific pattern needed |
| **Workflows** | `.claude/skills/` | Skill source corpus | When performing task |
| **Specialists** | `.claude/agents/` | Claude-native domain expertise | When domain knowledge needed |
| **Commands** | `.claude/commands/` | Claude slash-command entry points | When user uses /command |
| **Templates** | `agent_tasks/tasks/` | Reusable workflows | When executing structured task |
| **Folder-Based Claude Agents** | `.claude/agents/<name>/` | Complete Claude-native automation folders | When a Claude workflow needs that agent |

---

## Benefits of This Architecture

### For AI Assistants
- ✅ **Progressive disclosure** reduces context overload
- ✅ **Hierarchical structure** enables efficient navigation
- ✅ **Cross-references** build complete mental models
- ✅ **Templates** provide proven patterns

### For Developers
- ✅ **Organized knowledge** easy to update
- ✅ **No duplication** reduces maintenance
- ✅ **Clear structure** aids onboarding
- ✅ **Patterns documented** enable consistency

### For Users
- ✅ **Slash commands** provide simple entry points
- ✅ **Task templates** ensure repeatability
- ✅ **Skills** encapsulate workflows
- ✅ **Documentation** generated from structure

---

## Related Documentation

- [Architecture](architecture.md) - Technical architecture and design decisions
- [Agent Instructions Guide](claude_md.md) - Shared AGENTS/CLAUDE loading model
- [Contributing](contributing.md) - How to contribute to the project
- [Style Guide](style_guide.md) - Coding standards and patterns

---

## Next Steps

**For Claude**: Follow the shared loading pattern:
1. Read `CLAUDE.md`
2. Follow `@AGENTS.md`
3. Use `.claude/MANIFEST.md` for Claude-native discovery
4. Load specific rules, skills, and subagents as needed

**For Developers**: Maintain the architecture:
1. Put shared rules in `AGENTS.md`
2. Keep `CLAUDE.md` as a loader
3. Create skills for common workflows
4. Update `.claude/MANIFEST.md` and `.claude/INDEX.md` when adding Claude components
