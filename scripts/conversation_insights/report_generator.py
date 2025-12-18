"""
Generate human-readable reports from conversation insights.
"""

from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime

try:
    from .conversation_parser import ConversationHistory, ConversationSession
    from .pattern_analyzer import PatternAnalyzer
    from .insight_extractor import InsightExtractor
except ImportError:
    from conversation_parser import ConversationHistory, ConversationSession
    from pattern_analyzer import PatternAnalyzer
    from insight_extractor import InsightExtractor


class ReportGenerator:
    """Generate reports from conversation insights."""

    def __init__(self, sessions: List[ConversationSession], output_dir: Optional[Path] = None):
        """Initialize report generator.

        Args:
            sessions: List of conversation sessions.
            output_dir: Output directory for reports (default: agent_tasks/).
        """
        self.sessions = sessions
        self.analyzer = PatternAnalyzer(sessions)
        self.extractor = InsightExtractor(sessions)

        if output_dir is None:
            output_dir = Path("agent_tasks")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)

    def generate_quick_insights(self) -> str:
        """Generate quick insights summary.

        Returns:
            Markdown formatted insights.
        """
        slash_commands = self.analyzer.find_slash_command_candidates()
        blockers = self.extractor.extract_blockers()

        report = ["# Quick Conversation Insights\n"]
        report.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        report.append(f"**Sessions analyzed**: {len(self.sessions)}\n")

        # Slash command suggestions
        report.append("\n## Suggested Slash Commands\n")
        if slash_commands:
            for cmd in slash_commands[:5]:
                report.append(f"### `/{cmd.suggested_name}` ({cmd.frequency} uses)\n")
                report.append(f"**Description**: {cmd.suggested_description}\n")
                report.append(f"**Example**: {cmd.example_prompts[0][:100]}...\n")
        else:
            report.append("*No recurring patterns detected for slash commands*\n")

        # Top blockers
        report.append("\n## Top Blockers\n")
        if blockers:
            for blocker in blockers[:3]:
                report.append(f"### {blocker.category.title()} ({blocker.frequency} occurrences)\n")
                report.append(f"**Issue**: {blocker.description}\n")
                if blocker.suggested_fix:
                    report.append(f"**Suggested fix**: {blocker.suggested_fix}\n")
        else:
            report.append("*No significant blockers detected*\n")

        return "\n".join(report)

    def generate_full_report(self) -> str:
        """Generate comprehensive insights report.

        Returns:
            Markdown formatted full report.
        """
        slash_commands = self.analyzer.find_slash_command_candidates()
        activities = self.analyzer.analyze_project_activity()
        workflows = self.analyzer.get_common_workflows()
        blockers = self.extractor.extract_blockers()
        best_practices = self.extractor.extract_best_practices()
        design_patterns = self.extractor.extract_design_patterns()

        report = ["# HMS-Commander Conversation Intelligence Report\n"]
        report.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report.append(f"**Sessions analyzed**: {len(self.sessions)}\n")

        # Executive summary
        report.append("\n## Executive Summary\n")
        total_messages = sum(len(s.messages) for s in self.sessions)
        total_prompts = sum(len(s.user_prompts()) for s in self.sessions)
        report.append(f"- Total messages: {total_messages}\n")
        report.append(f"- User prompts: {total_prompts}\n")
        report.append(f"- Projects active: {len(activities)}\n")
        report.append(f"- Slash command candidates: {len(slash_commands)}\n")
        report.append(f"- Blockers identified: {len(blockers)}\n")

        # Project activity
        report.append("\n## Project Activity\n")
        if activities:
            for project_path, activity in activities.items():
                project_name = Path(project_path).name
                report.append(f"\n### {project_name}\n")
                report.append(f"- Path: `{project_path}`\n")
                report.append(f"- Sessions: {activity.session_count}\n")
                report.append(f"- Messages: {activity.message_count}\n")
                report.append(f"- Date range: {activity.date_range[0]} to {activity.date_range[1]}\n")
                report.append(f"- Top topics: {', '.join(activity.top_topics[:5])}\n")
        else:
            report.append("*No project-specific activity*\n")

        # Slash commands
        report.append("\n## Slash Command Candidates\n")
        report.append("\nBased on recurring patterns, consider creating these slash commands:\n")
        if slash_commands:
            for i, cmd in enumerate(slash_commands, 1):
                report.append(f"\n### {i}. `/{cmd.suggested_name}` ({cmd.frequency} uses)\n")
                report.append(f"**Description**: {cmd.suggested_description}\n")
                report.append(f"**Pattern**: {cmd.pattern}\n")
                report.append("\n**Example prompts**:\n")
                for example in cmd.example_prompts[:3]:
                    report.append(f"- {example[:150]}...\n")
        else:
            report.append("*No patterns with sufficient frequency detected*\n")

        # Common workflows
        report.append("\n## Common Workflows\n")
        if workflows:
            report.append(f"\nIdentified {len(workflows)} multi-step workflow sessions:\n")
            for i, workflow in enumerate(workflows[:5], 1):
                report.append(f"\n### Workflow {i}\n")
                report.append(f"**Session**: {workflow['session_id']}\n")
                report.append(f"**Date**: {workflow['timestamp'].strftime('%Y-%m-%d')}\n")
                report.append("**Steps**:\n")
                for step_type, step_prompt in workflow['steps']:
                    report.append(f"- {step_type}: {step_prompt[:100]}...\n")
        else:
            report.append("*No multi-step workflows detected*\n")

        # Blockers
        report.append("\n## Blockers & Issues\n")
        if blockers:
            for i, blocker in enumerate(blockers, 1):
                report.append(f"\n### {i}. {blocker.category.title()} Issues ({blocker.frequency} occurrences)\n")
                report.append(f"**Description**: {blocker.description}\n")
                if blocker.suggested_fix:
                    report.append(f"**Suggested fix**: {blocker.suggested_fix}\n")
                report.append(f"**Example sessions**: {', '.join(blocker.example_sessions[:2])}\n")
        else:
            report.append("*No significant blockers detected*\n")

        # Best practices
        report.append("\n## Discovered Best Practices\n")
        if best_practices:
            by_category: Dict[str, List] = {}
            for practice in best_practices:
                if practice.category not in by_category:
                    by_category[practice.category] = []
                by_category[practice.category].append(practice)

            for category, practices in by_category.items():
                report.append(f"\n### {category.title()}\n")
                for practice in practices:
                    report.append(f"\n**{practice.title}**\n")
                    report.append(f"{practice.description}\n")
        else:
            report.append("*No patterns identified as best practices yet*\n")

        # Design patterns
        report.append("\n## HMS-Commander Design Patterns\n")
        if design_patterns:
            for i, pattern in enumerate(design_patterns, 1):
                report.append(f"\n### {i}. {pattern.name}\n")
                report.append(f"**Description**: {pattern.description}\n")
                report.append(f"**Use cases**: {', '.join(pattern.use_cases)}\n")
                if pattern.code_example:
                    report.append("\n**Example**:\n```python\n")
                    report.append(f"{pattern.code_example}\n```\n")
        else:
            report.append("*No code patterns identified yet*\n")

        # Recommendations
        report.append("\n## Recommendations\n")
        report.append("\nBased on this analysis:\n")

        if slash_commands:
            report.append(f"\n1. **Create {len(slash_commands)} slash commands** for frequent operations\n")
        if blockers:
            top_blocker = blockers[0]
            report.append(f"\n2. **Address {top_blocker.category} issues** ({top_blocker.frequency} occurrences)\n")
        if workflows:
            report.append(f"\n3. **Document {len(workflows)} common workflows** for future reference\n")
        if best_practices:
            report.append(f"\n4. **Codify {len(best_practices)} best practices** in documentation\n")

        report.append("\n---\n")
        report.append("*Generated by HMS-Commander Conversation Intelligence*\n")

        return "\n".join(report)

    def save_quick_insights(self, filename: str = "conversation_insights_quick.md") -> Path:
        """Save quick insights to file.

        Args:
            filename: Output filename.

        Returns:
            Path to saved file.
        """
        content = self.generate_quick_insights()
        output_path = self.output_dir / filename

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return output_path

    def save_full_report(self, filename: str = "conversation_insights_full.md") -> Path:
        """Save full report to file.

        Args:
            filename: Output filename.

        Returns:
            Path to saved file.
        """
        content = self.generate_full_report()
        output_path = self.output_dir / filename

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return output_path


def quick_insights(project_path: Optional[str] = None, limit: int = 20) -> str:
    """Quick helper to generate insights.

    Args:
        project_path: Filter to specific project, or None for all.
        limit: Maximum sessions to analyze.

    Returns:
        Markdown formatted insights.
    """
    history = ConversationHistory()

    if project_path:
        sessions = history.get_project_sessions(project_path, limit=limit)
    else:
        sessions = history.get_recent_sessions(limit=limit)

    generator = ReportGenerator(sessions)
    return generator.generate_quick_insights()


def full_report(project_path: Optional[str] = None, limit: int = 50, output_dir: Optional[Path] = None) -> Path:
    """Quick helper to generate and save full report.

    Args:
        project_path: Filter to specific project, or None for all.
        limit: Maximum sessions to analyze.
        output_dir: Output directory (default: agent_tasks/).

    Returns:
        Path to saved report file.
    """
    history = ConversationHistory()

    if project_path:
        sessions = history.get_project_sessions(project_path, limit=limit)
    else:
        sessions = history.get_recent_sessions(limit=limit)

    generator = ReportGenerator(sessions, output_dir=output_dir)
    return generator.save_full_report()
