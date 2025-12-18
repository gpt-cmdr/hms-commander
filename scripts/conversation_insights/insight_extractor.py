"""
Extract actionable insights from conversation patterns.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import re

try:
    from .conversation_parser import ConversationSession, MessageType
    from .pattern_analyzer import PatternAnalyzer
except ImportError:
    from conversation_parser import ConversationSession, MessageType
    from pattern_analyzer import PatternAnalyzer


@dataclass
class Blocker:
    """Issue blocking progress."""
    category: str
    description: str
    frequency: int
    example_sessions: List[str]
    suggested_fix: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "category": self.category,
            "description": self.description,
            "frequency": self.frequency,
            "example_sessions": self.example_sessions,
            "suggested_fix": self.suggested_fix
        }


@dataclass
class BestPractice:
    """Discovered best practice pattern."""
    title: str
    description: str
    examples: List[str]
    category: str

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "examples": self.examples,
            "category": self.category
        }


@dataclass
class DesignPattern:
    """Code or workflow pattern that emerged."""
    name: str
    description: str
    use_cases: List[str]
    code_example: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "use_cases": use_cases,
            "code_example": self.code_example
        }


class InsightExtractor:
    """Extract actionable insights from conversation history."""

    # HMS-specific category keywords
    CATEGORY_KEYWORDS = {
        "execution": ["execute", "run", "compute", "jython", "hms_cmdr"],
        "basin": ["basin", "subbasin", "junction", "reach", "loss method", "transform"],
        "met": ["met", "precipitation", "gage", "atlas 14", "frequency storm"],
        "dss": ["dss", "results", "hydrograph", "time series", "peak flow"],
        "documentation": ["documentation", "readme", "mkdocs", "notebook"],
        "testing": ["test", "pytest", "example", "validation"],
        "git": ["git", "commit", "branch", "merge", "push"],
        "imports": ["import", "module", "package", "dependency"],
        "paths": ["path", "file", "directory", "folder"],
        "calibration": ["calibration", "nse", "rmse", "pbias", "objective"]
    }

    def __init__(self, sessions: List[ConversationSession]):
        """Initialize with conversation sessions.

        Args:
            sessions: List of conversation sessions to analyze.
        """
        self.sessions = sessions
        self.analyzer = PatternAnalyzer(sessions)

    def extract_blockers(self) -> List[Blocker]:
        """Find recurring blockers and issues.

        Returns:
            List of blockers sorted by frequency.
        """
        blocker_mentions = self.analyzer.get_blocker_mentions()

        # Group by category
        categorized: Dict[str, List[Dict]] = {}
        for mention in blocker_mentions:
            category = self._categorize_text(mention["prompt"])
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(mention)

        # Create blocker objects
        blockers = []
        for category, mentions in categorized.items():
            if len(mentions) >= 2:  # At least 2 occurrences
                blocker = Blocker(
                    category=category,
                    description=self._summarize_blocker(mentions),
                    frequency=len(mentions),
                    example_sessions=[m["session_id"] for m in mentions[:3]],
                    suggested_fix=self._suggest_fix(category, mentions)
                )
                blockers.append(blocker)

        return sorted(blockers, key=lambda b: b.frequency, reverse=True)

    def extract_best_practices(self) -> List[BestPractice]:
        """Identify successful patterns that could become best practices.

        Returns:
            List of discovered best practices.
        """
        practices = []

        # Look for successful workflows (prompts followed by positive responses)
        for session in self.sessions:
            messages = session.messages
            for i, msg in enumerate(messages):
                if msg.type == MessageType.USER and i + 1 < len(messages):
                    response = messages[i + 1]
                    if response.type == MessageType.ASSISTANT:
                        # Check for success indicators
                        if self._is_successful_outcome(response.content):
                            category = self._categorize_text(msg.content)
                            practice = self._create_best_practice(msg.content, response.content, category)
                            if practice:
                                practices.append(practice)

        # Deduplicate by title
        seen_titles = set()
        unique_practices = []
        for practice in practices:
            if practice.title not in seen_titles:
                seen_titles.add(practice.title)
                unique_practices.append(practice)

        return unique_practices[:10]  # Top 10

    def extract_design_patterns(self) -> List[DesignPattern]:
        """Identify recurring design patterns in code discussions.

        Returns:
            List of design patterns.
        """
        patterns = []

        # Look for code-related discussions
        for session in self.sessions:
            for msg in session.messages:
                if msg.type == MessageType.ASSISTANT and "```" in msg.content:
                    # Extract code blocks
                    code_blocks = re.findall(r'```[\w]*\n(.*?)```', msg.content, re.DOTALL)
                    for code in code_blocks:
                        pattern = self._identify_pattern(code)
                        if pattern:
                            patterns.append(pattern)

        # Deduplicate
        seen_names = set()
        unique_patterns = []
        for pattern in patterns:
            if pattern.name not in seen_names:
                seen_names.add(pattern.name)
                unique_patterns.append(pattern)

        return unique_patterns[:5]  # Top 5

    def _categorize_text(self, text: str) -> str:
        """Categorize text based on keywords.

        Args:
            text: Text to categorize.

        Returns:
            Category name or "general".
        """
        text_lower = text.lower()
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            if any(keyword in text_lower for keyword in keywords):
                return category
        return "general"

    def _summarize_blocker(self, mentions: List[Dict]) -> str:
        """Create summary description for blocker.

        Args:
            mentions: List of blocker mentions.

        Returns:
            Summary description.
        """
        # Extract common error patterns
        prompts = [m["prompt"] for m in mentions]
        common_words = self._find_common_words(prompts)
        return f"Issues related to {', '.join(common_words[:5])}"

    def _suggest_fix(self, category: str, mentions: List[Dict]) -> Optional[str]:
        """Suggest a fix based on category and mentions.

        Args:
            category: Issue category.
            mentions: List of blocker mentions.

        Returns:
            Suggested fix or None.
        """
        fixes = {
            "execution": "Check HMS installation path and version compatibility",
            "basin": "Verify basin file syntax and parameter ranges",
            "met": "Ensure precipitation data is properly formatted",
            "dss": "Check DSS file paths and pathname conventions",
            "imports": "Verify package installation and Python path",
            "paths": "Use absolute paths and verify file existence"
        }
        return fixes.get(category)

    def _is_successful_outcome(self, response: str) -> bool:
        """Check if response indicates success.

        Args:
            response: Assistant response.

        Returns:
            True if successful outcome.
        """
        success_indicators = [
            "successfully", "completed", "works", "correct",
            "done", "created", "updated", "extracted"
        ]
        response_lower = response.lower()
        return any(indicator in response_lower for indicator in success_indicators)

    def _create_best_practice(self, prompt: str, response: str, category: str) -> Optional[BestPractice]:
        """Create best practice from successful interaction.

        Args:
            prompt: User prompt.
            response: Assistant response.
            category: Category.

        Returns:
            BestPractice or None.
        """
        # Extract action from prompt
        action_match = re.search(r'\b(create|update|extract|run|execute|validate)\b', prompt.lower())
        if not action_match:
            return None

        action = action_match.group(1)
        title = f"{action.title()} {category} effectively"

        # Extract key steps from response
        steps = re.findall(r'\d+\.\s*([^\n]+)', response)
        if not steps:
            return None

        description = " → ".join(steps[:3])

        return BestPractice(
            title=title,
            description=description,
            examples=[prompt],
            category=category
        )

    def _identify_pattern(self, code: str) -> Optional[DesignPattern]:
        """Identify design pattern from code.

        Args:
            code: Code snippet.

        Returns:
            DesignPattern or None.
        """
        code_lower = code.lower()

        # Check for HMS-specific patterns
        if "init_hms_project" in code_lower:
            return DesignPattern(
                name="Project Initialization Pattern",
                description="Initialize HMS project for API access",
                use_cases=["Project setup", "Global state management"],
                code_example=code[:200]
            )
        elif "hmsbasin." in code_lower or "hmsmet." in code_lower:
            return DesignPattern(
                name="Static Method Pattern",
                description="Use static methods for HMS file operations",
                use_cases=["File parsing", "Model updates"],
                code_example=code[:200]
            )
        elif "hmscmdr.compute_run" in code_lower:
            return DesignPattern(
                name="Execution Pattern",
                description="Execute HMS simulations programmatically",
                use_cases=["Automation", "Batch processing"],
                code_example=code[:200]
            )

        return None

    def _find_common_words(self, texts: List[str], min_count: int = 2) -> List[str]:
        """Find common words across texts.

        Args:
            texts: List of texts.
            min_count: Minimum occurrences.

        Returns:
            List of common words.
        """
        from collections import Counter
        words = []
        for text in texts:
            words.extend(re.findall(r'\b\w{4,}\b', text.lower()))

        counter = Counter(words)
        return [word for word, count in counter.most_common() if count >= min_count]
