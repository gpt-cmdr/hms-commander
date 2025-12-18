"""
Conversation Insights - Utilities for analyzing Claude Code conversation history.
"""

from .conversation_parser import (
    ConversationHistory,
    ConversationMessage,
    ConversationSession,
    HistoryEntry,
    MessageType,
    get_recent_prompts,
    get_project_conversations,
    encode_project_path,
    decode_project_path,
)
from .pattern_analyzer import (
    PatternAnalyzer,
    SlashCommandCandidate,
    ProjectActivity,
)
from .insight_extractor import (
    InsightExtractor,
    Blocker,
    BestPractice,
    DesignPattern,
)
from .report_generator import (
    ReportGenerator,
    quick_insights,
    full_report,
)

__all__ = [
    # Parser
    "ConversationHistory",
    "ConversationMessage",
    "ConversationSession",
    "HistoryEntry",
    "MessageType",
    "get_recent_prompts",
    "get_project_conversations",
    "encode_project_path",
    "decode_project_path",
    # Pattern Analyzer
    "PatternAnalyzer",
    "SlashCommandCandidate",
    "ProjectActivity",
    # Insight Extractor
    "InsightExtractor",
    "Blocker",
    "BestPractice",
    "DesignPattern",
    # Report Generator
    "ReportGenerator",
    "quick_insights",
    "full_report",
]
