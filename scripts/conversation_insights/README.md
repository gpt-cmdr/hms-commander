# Conversation Insights

Python utilities for analyzing Claude Code conversation history to extract actionable insights.

## Purpose

Parse `~/.claude/history.jsonl` and conversation files to:
- Identify recurring patterns that suggest slash commands
- Detect blockers and issues
- Extract best practices from successful interactions
- Analyze project activity and workflows
- Generate intelligence reports for development planning

## Installation

No installation required. Import directly from scripts:

```python
import sys
sys.path.insert(0, 'scripts')
from conversation_insights import *
```

## Quick Start

### Get Recent User Prompts

```python
from conversation_insights import get_recent_prompts

# Last 20 prompts across all projects
prompts = get_recent_prompts(limit=20)

# Last 20 prompts for specific project
prompts = get_recent_prompts(project_path=r"C:\GH\hms-commander", limit=20)
```

### Generate Quick Insights

```python
from conversation_insights import quick_insights

# Quick insights for all recent conversations
report = quick_insights(limit=20)
print(report)

# Quick insights for specific project
report = quick_insights(project_path=r"C:\GH\hms-commander", limit=50)
```

### Generate Full Intelligence Report

```python
from conversation_insights import full_report

# Full report saved to agent_tasks/
output_path = full_report(limit=50)
print(f"Report saved to: {output_path}")

# Project-specific report
output_path = full_report(
    project_path=r"C:\GH\hms-commander",
    limit=100,
    output_dir="agent_tasks"
)
```

## Advanced Usage

### Parse Conversation History

```python
from conversation_insights import ConversationHistory

history = ConversationHistory()

# Load session metadata
entries = history.load_history()

# Get recent sessions
sessions = history.get_recent_sessions(limit=10)

# Get project-specific sessions
sessions = history.get_project_sessions(r"C:\GH\hms-commander", limit=20)

# Load specific conversation
session = history.load_conversation("session-id-here")
```

### Analyze Patterns

```python
from conversation_insights import PatternAnalyzer

analyzer = PatternAnalyzer(sessions)

# Find slash command candidates
candidates = analyzer.find_slash_command_candidates(min_frequency=3)
for cmd in candidates:
    print(f"/{cmd.suggested_name}: {cmd.description} ({cmd.frequency} uses)")

# Analyze project activity
activities = analyzer.analyze_project_activity()
for project_path, activity in activities.items():
    print(f"{project_path}: {activity.session_count} sessions")

# Find common workflows
workflows = analyzer.get_common_workflows()

# Find blocker mentions
blockers = analyzer.get_blocker_mentions()
```

### Extract Insights

```python
from conversation_insights import InsightExtractor

extractor = InsightExtractor(sessions)

# Extract blockers
blockers = extractor.extract_blockers()
for blocker in blockers:
    print(f"{blocker.category}: {blocker.description} ({blocker.frequency}x)")

# Extract best practices
practices = extractor.extract_best_practices()
for practice in practices:
    print(f"{practice.title} ({practice.category})")

# Extract design patterns
patterns = extractor.extract_design_patterns()
for pattern in patterns:
    print(f"{pattern.name}: {pattern.description}")
```

### Generate Custom Reports

```python
from conversation_insights import ReportGenerator

generator = ReportGenerator(sessions, output_dir="agent_tasks")

# Quick insights (markdown string)
quick = generator.generate_quick_insights()
print(quick)

# Full report (markdown string)
full = generator.generate_full_report()

# Save to files
quick_path = generator.save_quick_insights()
full_path = generator.save_full_report()
```

## Module Structure

```
conversation_insights/
├── __init__.py              # Package exports
├── conversation_parser.py   # Parse ~/.claude/history.jsonl and conversations
├── pattern_analyzer.py      # Identify patterns and workflows
├── insight_extractor.py     # Extract actionable insights (HMS-adapted)
├── report_generator.py      # Generate markdown reports
└── README.md               # This file
```

## HMS-Specific Adaptations

### Category Keywords

HMS-specific categories for insight extraction:
- **execution**: HMS simulation execution (HmsCmdr, Jython)
- **basin**: Basin model operations (subbasins, loss methods, transforms)
- **met**: Meteorologic models (precipitation, gages, Atlas 14)
- **dss**: DSS results operations (hydrographs, time series, peaks)
- **calibration**: Model calibration (NSE, RMSE, PBIAS)

### Known Patterns

HMS-specific slash command patterns:
- `/run-hms`: Execute HEC-HMS simulation
- `/update-basin`: Update basin model parameters
- `/extract-results`: Extract simulation results from DSS
- `/update-met`: Update meteorologic model
- `/project-status`: Show project status
- `/validate`: Validate model configuration

## Output

Reports are saved to `agent_tasks/` by default:
- `conversation_insights_quick.md`: Quick summary of top insights
- `conversation_insights_full.md`: Comprehensive analysis report

## Data Sources

### ~/.claude/history.jsonl
Session metadata (session IDs, timestamps, project paths)

### ~/.claude/conversations/{session-id}.json
Full conversation messages for each session

## Use Cases

1. **Slash Command Creation**: Identify recurring prompts to automate
2. **Blocker Detection**: Find common issues blocking progress
3. **Best Practice Extraction**: Document successful workflows
4. **Design Pattern Discovery**: Codify emerging code patterns
5. **Project Activity Tracking**: Monitor development trends
6. **Development Planning**: Data-driven sprint planning

## Integration with Phase 1.5

Part of Sprint 3: Conversation Intelligence
- Informs slash command creation (Sprint 4)
- Supports documentation generation (Sprint 5)
- Enables memory refinement (Sprint 6)

## Notes

- All paths should be absolute (Windows: `C:\...`, Unix: `/home/...`)
- Project paths are base64-encoded in history.jsonl
- Reports use markdown format for easy viewing
- Standalone usage (no hms-commander dependency)
