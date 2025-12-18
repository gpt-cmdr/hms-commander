"""
Analyze conversation patterns for slash command candidates and project activity.
"""

from dataclasses import dataclass
from typing import List, Dict, Set, Optional
from collections import Counter
import re

try:
    from .conversation_parser import ConversationSession, MessageType
except ImportError:
    from conversation_parser import ConversationSession, MessageType


@dataclass
class SlashCommandCandidate:
    """Candidate for creating a slash command."""
    pattern: str
    frequency: int
    example_prompts: List[str]
    suggested_name: str
    suggested_description: str

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "pattern": self.pattern,
            "frequency": self.frequency,
            "example_prompts": self.example_prompts,
            "suggested_name": self.suggested_name,
            "suggested_description": self.suggested_description
        }


@dataclass
class ProjectActivity:
    """Project activity summary."""
    project_path: str
    session_count: int
    message_count: int
    user_prompt_count: int
    top_topics: List[str]
    date_range: tuple[str, str]

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "project_path": self.project_path,
            "session_count": self.session_count,
            "message_count": self.message_count,
            "user_prompt_count": self.user_prompt_count,
            "top_topics": self.top_topics,
            "date_range": list(self.date_range)
        }


class PatternAnalyzer:
    """Analyze patterns in conversation history."""

    # Known repetitive patterns that suggest slash commands
    KNOWN_PATTERNS = {
        "run_simulation": {
            "keywords": ["execute", "run", "compute", "simulation"],
            "name": "run-hms",
            "description": "Execute HEC-HMS simulation"
        },
        "update_basin": {
            "keywords": ["update", "modify", "change", "basin", "subbasin"],
            "name": "update-basin",
            "description": "Update basin model parameters"
        },
        "extract_results": {
            "keywords": ["extract", "get", "read", "results", "dss", "peak"],
            "name": "extract-results",
            "description": "Extract simulation results from DSS"
        },
        "update_met": {
            "keywords": ["update", "met", "precipitation", "gage", "atlas"],
            "name": "update-met",
            "description": "Update meteorologic model"
        },
        "check_status": {
            "keywords": ["check", "status", "show", "list", "project"],
            "name": "project-status",
            "description": "Show project status and configuration"
        },
        "validate_model": {
            "keywords": ["validate", "verify", "check", "test", "model"],
            "name": "validate",
            "description": "Validate model configuration"
        }
    }

    def __init__(self, sessions: List[ConversationSession]):
        """Initialize with conversation sessions.

        Args:
            sessions: List of conversation sessions to analyze.
        """
        self.sessions = sessions

    def find_slash_command_candidates(self, min_frequency: int = 3) -> List[SlashCommandCandidate]:
        """Find patterns that occur frequently enough to warrant slash commands.

        Args:
            min_frequency: Minimum number of occurrences to suggest a command.

        Returns:
            List of slash command candidates sorted by frequency.
        """
        pattern_matches: Dict[str, List[str]] = {pattern: [] for pattern in self.KNOWN_PATTERNS}

        # Collect matching prompts
        for session in self.sessions:
            for prompt in session.user_prompts():
                prompt_lower = prompt.lower()
                for pattern_id, pattern_info in self.KNOWN_PATTERNS.items():
                    if any(keyword in prompt_lower for keyword in pattern_info["keywords"]):
                        pattern_matches[pattern_id].append(prompt)

        # Create candidates
        candidates = []
        for pattern_id, prompts in pattern_matches.items():
            if len(prompts) >= min_frequency:
                pattern_info = self.KNOWN_PATTERNS[pattern_id]
                candidate = SlashCommandCandidate(
                    pattern=pattern_id,
                    frequency=len(prompts),
                    example_prompts=prompts[:5],  # Limit examples
                    suggested_name=pattern_info["name"],
                    suggested_description=pattern_info["description"]
                )
                candidates.append(candidate)

        return sorted(candidates, key=lambda c: c.frequency, reverse=True)

    def analyze_project_activity(self) -> Dict[str, ProjectActivity]:
        """Analyze activity by project.

        Returns:
            Dictionary mapping project paths to activity summaries.
        """
        project_sessions: Dict[str, List[ConversationSession]] = {}

        # Group sessions by project
        for session in self.sessions:
            if session.project_path:
                if session.project_path not in project_sessions:
                    project_sessions[session.project_path] = []
                project_sessions[session.project_path].append(session)

        # Analyze each project
        activities = {}
        for project_path, sessions in project_sessions.items():
            activities[project_path] = self._analyze_single_project(project_path, sessions)

        return activities

    def _analyze_single_project(self, project_path: str, sessions: List[ConversationSession]) -> ProjectActivity:
        """Analyze activity for a single project.

        Args:
            project_path: Path to project.
            sessions: List of sessions for this project.

        Returns:
            ProjectActivity summary.
        """
        message_count = sum(len(session.messages) for session in sessions)
        user_prompt_count = sum(len(session.user_prompts()) for session in sessions)

        # Extract topics from prompts
        all_prompts = []
        for session in sessions:
            all_prompts.extend(session.user_prompts())

        topics = self._extract_topics(all_prompts)

        # Date range
        timestamps = [session.timestamp for session in sessions]
        date_range = (
            min(timestamps).strftime("%Y-%m-%d"),
            max(timestamps).strftime("%Y-%m-%d")
        )

        return ProjectActivity(
            project_path=project_path,
            session_count=len(sessions),
            message_count=message_count,
            user_prompt_count=user_prompt_count,
            top_topics=topics[:10],
            date_range=date_range
        )

    def _extract_topics(self, prompts: List[str]) -> List[str]:
        """Extract common topics from prompts.

        Args:
            prompts: List of user prompts.

        Returns:
            List of topics sorted by frequency.
        """
        # Simple keyword extraction
        keywords = []
        for prompt in prompts:
            words = re.findall(r'\b\w+\b', prompt.lower())
            # Filter out common words
            filtered = [w for w in words if len(w) > 3 and w not in {
                'that', 'this', 'with', 'from', 'have', 'what', 'when', 'where',
                'which', 'would', 'could', 'should', 'please', 'need', 'want'
            }]
            keywords.extend(filtered)

        # Count and return top topics
        counter = Counter(keywords)
        return [word for word, count in counter.most_common(20)]

    def get_common_workflows(self) -> List[Dict[str, any]]:
        """Identify common multi-step workflows.

        Returns:
            List of workflow patterns with steps and frequency.
        """
        workflows = []

        # Look for sessions with multiple related prompts
        for session in self.sessions:
            prompts = session.user_prompts()
            if len(prompts) < 2:
                continue

            # Detect workflow sequences
            workflow_steps = []
            for prompt in prompts:
                prompt_lower = prompt.lower()
                if any(kw in prompt_lower for kw in ["first", "start", "initialize", "create"]):
                    workflow_steps.append(("initialize", prompt))
                elif any(kw in prompt_lower for kw in ["then", "next", "after", "now"]):
                    workflow_steps.append(("continue", prompt))
                elif any(kw in prompt_lower for kw in ["finally", "last", "verify", "check"]):
                    workflow_steps.append(("finalize", prompt))

            if len(workflow_steps) >= 2:
                workflows.append({
                    "session_id": session.session_id,
                    "steps": workflow_steps,
                    "timestamp": session.timestamp
                })

        return workflows

    def get_blocker_mentions(self) -> List[Dict[str, any]]:
        """Find mentions of blockers or issues.

        Returns:
            List of potential blockers mentioned in conversations.
        """
        blockers = []
        blocker_keywords = [
            "error", "fail", "broken", "issue", "problem", "bug",
            "doesn't work", "not working", "can't", "unable"
        ]

        for session in self.sessions:
            for prompt in session.user_prompts():
                prompt_lower = prompt.lower()
                if any(keyword in prompt_lower for keyword in blocker_keywords):
                    blockers.append({
                        "session_id": session.session_id,
                        "timestamp": session.timestamp,
                        "prompt": prompt,
                        "project": session.project_path
                    })

        return blockers
