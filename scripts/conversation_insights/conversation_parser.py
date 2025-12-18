"""
Parse Claude Code conversation history from ~/.claude/history.jsonl and project files.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Any
import base64


class MessageType(Enum):
    """Message type in conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class ConversationMessage:
    """Single message in a conversation."""
    type: MessageType
    content: str
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


@dataclass
class HistoryEntry:
    """Entry in ~/.claude/history.jsonl (session metadata)."""
    session_id: str
    project_path: Optional[str]
    timestamp: datetime
    title: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "project_path": self.project_path,
            "timestamp": self.timestamp.isoformat(),
            "title": self.title
        }


@dataclass
class ConversationSession:
    """Complete conversation session with messages."""
    session_id: str
    project_path: Optional[str]
    timestamp: datetime
    messages: List[ConversationMessage]
    title: Optional[str] = None

    def user_prompts(self) -> List[str]:
        """Extract all user prompts."""
        return [msg.content for msg in self.messages if msg.type == MessageType.USER]

    def assistant_responses(self) -> List[str]:
        """Extract all assistant responses."""
        return [msg.content for msg in self.messages if msg.type == MessageType.ASSISTANT]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "project_path": self.project_path,
            "timestamp": self.timestamp.isoformat(),
            "title": self.title,
            "messages": [msg.to_dict() for msg in self.messages]
        }


class ConversationHistory:
    """Parse and analyze Claude Code conversation history."""

    def __init__(self, claude_dir: Optional[Path] = None):
        """Initialize with Claude directory path.

        Args:
            claude_dir: Path to ~/.claude directory. If None, uses default.
        """
        if claude_dir is None:
            claude_dir = Path.home() / ".claude"
        self.claude_dir = Path(claude_dir)
        self.history_file = self.claude_dir / "history.jsonl"
        self.conversations_dir = self.claude_dir / "conversations"

    def load_history(self) -> List[HistoryEntry]:
        """Load session metadata from history.jsonl.

        Returns:
            List of history entries sorted by timestamp (newest first).
        """
        if not self.history_file.exists():
            return []

        entries = []
        with open(self.history_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())

                    # Parse timestamp (could be Unix ms, ISO string, or missing)
                    timestamp_value = data.get("timestamp")
                    if isinstance(timestamp_value, (int, float)):
                        # Unix timestamp in milliseconds
                        timestamp = datetime.fromtimestamp(timestamp_value / 1000.0)
                    elif isinstance(timestamp_value, str):
                        # ISO format string
                        timestamp = datetime.fromisoformat(timestamp_value)
                    else:
                        timestamp = datetime.now()

                    # Get project path (could be "project" or "projectPath")
                    project = data.get("projectPath") or data.get("project")

                    entry = HistoryEntry(
                        session_id=data.get("id", ""),
                        project_path=decode_project_path(project) if project else None,
                        timestamp=timestamp,
                        title=data.get("title") or data.get("display")
                    )
                    entries.append(entry)
                except (json.JSONDecodeError, ValueError, TypeError) as e:
                    print(f"Warning: Failed to parse history entry: {e}")
                    continue

        return sorted(entries, key=lambda e: e.timestamp, reverse=True)

    def load_conversation(self, session_id: str) -> Optional[ConversationSession]:
        """Load full conversation messages for a session.

        Args:
            session_id: Session ID to load.

        Returns:
            ConversationSession if found, None otherwise.
        """
        conv_file = self.conversations_dir / f"{session_id}.json"
        if not conv_file.exists():
            return None

        try:
            with open(conv_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            messages = []
            for msg in data.get("messages", []):
                msg_type = MessageType(msg.get("type", "user"))
                content = msg.get("content", "")
                timestamp_str = msg.get("timestamp")
                timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else None

                messages.append(ConversationMessage(
                    type=msg_type,
                    content=content,
                    timestamp=timestamp
                ))

            # Parse session timestamp
            timestamp_value = data.get("timestamp")
            if isinstance(timestamp_value, (int, float)):
                session_timestamp = datetime.fromtimestamp(timestamp_value / 1000.0)
            elif isinstance(timestamp_value, str):
                session_timestamp = datetime.fromisoformat(timestamp_value)
            else:
                session_timestamp = datetime.now()

            # Get project path
            project = data.get("projectPath") or data.get("project")

            return ConversationSession(
                session_id=data.get("id", session_id),
                project_path=decode_project_path(project) if project else None,
                timestamp=session_timestamp,
                messages=messages,
                title=data.get("title") or data.get("display")
            )
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"Warning: Failed to parse conversation {session_id}: {e}")
            return None

    def get_project_sessions(self, project_path: str, limit: Optional[int] = None) -> List[ConversationSession]:
        """Get all conversations for a specific project.

        Args:
            project_path: Absolute path to project directory.
            limit: Maximum number of sessions to return (most recent).

        Returns:
            List of conversation sessions sorted by timestamp (newest first).
        """
        history = self.load_history()
        project_path_normalized = str(Path(project_path).resolve())

        sessions = []
        for entry in history:
            if entry.project_path and Path(entry.project_path).resolve() == Path(project_path_normalized):
                session = self.load_conversation(entry.session_id)
                if session:
                    sessions.append(session)
                    if limit and len(sessions) >= limit:
                        break

        return sessions

    def get_recent_sessions(self, limit: int = 10) -> List[ConversationSession]:
        """Get most recent conversation sessions.

        Args:
            limit: Maximum number of sessions to return.

        Returns:
            List of conversation sessions sorted by timestamp (newest first).
        """
        history = self.load_history()
        sessions = []

        for entry in history[:limit]:
            session = self.load_conversation(entry.session_id)
            if session:
                sessions.append(session)

        return sessions


def encode_project_path(path: Optional[str]) -> Optional[str]:
    """Encode project path to base64 (as Claude Code does).

    Args:
        path: Absolute file path.

    Returns:
        Base64 encoded path, or None if path is None.
    """
    if path is None:
        return None
    return base64.b64encode(path.encode('utf-8')).decode('utf-8')


def decode_project_path(encoded: Optional[str]) -> Optional[str]:
    """Decode base64 project path (or return plain path if not encoded).

    Args:
        encoded: Base64 encoded path or plain path string.

    Returns:
        Decoded absolute path, or None if encoded is None.
    """
    if encoded is None:
        return None

    # Try base64 decode first
    try:
        decoded = base64.b64decode(encoded.encode('utf-8')).decode('utf-8')
        # Check if it looks like a path (contains / or \)
        if '/' in decoded or '\\' in decoded:
            return decoded
    except Exception:
        pass

    # If decode failed or doesn't look like a path, return as-is
    # (history.jsonl stores plain paths, conversations/*.json may use base64)
    return encoded


def get_recent_prompts(project_path: Optional[str] = None, limit: int = 20) -> List[str]:
    """Quick helper to get recent user prompts.

    Args:
        project_path: Filter to specific project, or None for all projects.
        limit: Maximum number of prompts to return.

    Returns:
        List of user prompt strings (newest first).
    """
    history = ConversationHistory()

    if project_path:
        sessions = history.get_project_sessions(project_path, limit=limit)
    else:
        sessions = history.get_recent_sessions(limit=limit)

    prompts = []
    for session in sessions:
        prompts.extend(session.user_prompts())
        if len(prompts) >= limit:
            break

    return prompts[:limit]


def get_project_conversations(project_path: str, limit: Optional[int] = None) -> List[ConversationSession]:
    """Quick helper to get project conversations.

    Args:
        project_path: Absolute path to project directory.
        limit: Maximum number of sessions to return.

    Returns:
        List of conversation sessions (newest first).
    """
    history = ConversationHistory()
    return history.get_project_sessions(project_path, limit=limit)
