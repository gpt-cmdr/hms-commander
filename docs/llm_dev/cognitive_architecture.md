# Cognitive Architecture

**Purpose**: Explain HMS Commander's hierarchical knowledge organization, progressive disclosure, and agent orchestration patterns.

---

## Overview

HMS Commander uses a sophisticated cognitive architecture that organizes knowledge hierarchically and enables progressive disclosure of context. This approach allows AI assistants to efficiently navigate from high-level concepts to detailed implementation patterns.

---

## Hierarchical Knowledge Structure

```mermaid
graph TB
    subgraph "Root Level - Entry Point"
        A[CLAUDE.md<br/>Primary Instructions]
    end

    subgraph "Framework Level - Organization"
        B[.claude/CLAUDE.md<br/>Hierarchical Hub]
        C[.claude/INDEX.md<br/>Framework Index]
    end

    subgraph "Pattern Level - Knowledge"
        D[.claude/rules/python/]
        E[.claude/rules/hec-hms/]
        F[.claude/rules/testing/]
        G[.claude/rules/documentation/]
        H[.claude/rules/project/]
        I[.claude/rules/integration/]
    end

    subgraph "Execution Level - Workflows"
        J[.claude/skills/<br/>Task Workflows]
        K[.claude/agents/<br/>Domain Specialists]
        L[.claude/commands/<br/>Slash Commands]
    end

    subgraph "Production Level - Automation"
        M[hms_agents/<br/>Production Agents]
        N[agent_tasks/<br/>Task Templates]
    end

    A --> B
    A --> C
    B --> D
    B --> E
    B --> F
    B --> G
    B --> H
    B --> I

    D --> J
    E --> J
    F --> J
    D --> K
    E --> K

    J --> L
    K --> L

    L --> M
    L --> N

    style A fill:#ffcccc
    style B fill:#ffe6cc
    style C fill:#ffe6cc
    style D fill:#e1f5ff
    style E fill:#e1f5ff
    style F fill:#e1f5ff
    style J fill:#fff4e1
    style K fill:#fff4e1
    style M fill:#e7f5e7
```

---

## Progressive Disclosure Pattern

The framework uses **@imports** to progressively disclose context:

```mermaid
flowchart LR
    A[User asks:<br/>'How do clone workflows work?'] --> B{Claude reads<br/>CLAUDE.md}

    B --> C[@import .claude/CLAUDE.md]
    C --> D[@import .claude/rules/hec-hms/clone-workflows.md]

    D --> E[Detailed Pattern:<br/>- Non-destructive clones<br/>- GUI verification<br/>- QAQC workflows]

    E --> F[Related Context:<br/>@import execution.md<br/>@import basin-files.md]

    F --> G[Claude has full context<br/>to answer question]

    style A fill:#e1f5ff
    style D fill:#fff4e1
    style G fill:#e7f5e7
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

    Claude->>Claude: Read CLAUDE.md<br/>Identify workflow type

    Claude->>Command: /hms-run
    Note over Command: Slash command expands prompt

    Command->>Claude: Execute workflow:<br/>1. Initialize project<br/>2. Update met model<br/>3. Run simulation

    Claude->>Task: Read agent_tasks/tasks/<br/>020-run-simulation.md
    Note over Task: Task template provides structure

    Task->>Skill: Activate skill:<br/>executing-hms-runs
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
        E1[executing-hms-runs]
        E2[parsing-basin-models]
        E3[updating-met-models]
        E4[investigating-hms-internals]
        E5[querying-hms-documentation]
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

    subgraph "Tier 3: Production Agents"
        C1[hms_agents/<br/>Full folders with tools/]
        C2[Purpose: Complete automation<br/>self-contained workflows]
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

### Level 1: Root Entry (CLAUDE.md)
```
User: "How do I execute HMS simulations?"

Claude reads: CLAUDE.md
├── Quick Start section
├── @import .claude/CLAUDE.md
└── Navigation to detailed docs
```

### Level 2: Framework Hub (.claude/CLAUDE.md)
```
Claude loads: .claude/CLAUDE.md
├── @import .claude/rules/hec-hms/execution.md
├── @import .claude/rules/testing/example-projects.md
└── Links to API reference
```

### Level 3: Pattern Details (execution.md)
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
- Each concept documented **once**
- Other documents **reference** via @imports
- No duplication = no drift

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
| **Entry** | `CLAUDE.md` | User-facing overview | Always |
| **Framework** | `.claude/CLAUDE.md` | Knowledge hub with @imports | When detailed context needed |
| **Patterns** | `.claude/rules/*/` | Architectural decisions | When specific pattern needed |
| **Workflows** | `.claude/skills/` | Task execution patterns | When performing task |
| **Specialists** | `.claude/agents/` | Domain expertise | When domain knowledge needed |
| **Commands** | `.claude/commands/` | User entry points | When user uses /command |
| **Templates** | `agent_tasks/tasks/` | Reusable workflows | When executing structured task |
| **Production** | `hms_agents/` | Complete automation | When running standalone agent |

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
- [CLAUDE.md Guide](claude_md.md) - Primary instructions for AI assistants
- [Contributing](contributing.md) - How to contribute to the project
- [Style Guide](style_guide.md) - Coding standards and patterns

---

## Next Steps

**For Claude**: Follow the hierarchical loading pattern:
1. Read CLAUDE.md (entry point)
2. Follow @imports to .claude/CLAUDE.md
3. Load specific rules as needed
4. Reference skills and subagents for execution

**For Developers**: Maintain the architecture:
1. Document patterns in `.claude/rules/`
2. Create skills for common workflows
3. Build subagents for domain expertise
4. Update INDEX.md when adding components
