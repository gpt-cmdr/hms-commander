"""
Test script for conversation_insights package.

Demonstrates basic usage of conversation intelligence utilities.
"""

import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

from conversation_insights import (
    ConversationHistory,
    PatternAnalyzer,
    InsightExtractor,
    ReportGenerator,
    get_recent_prompts,
    quick_insights,
)


def test_basic_parsing():
    """Test basic conversation parsing."""
    print("=" * 60)
    print("TEST: Basic Conversation Parsing")
    print("=" * 60)

    history = ConversationHistory()

    # Load recent history entries
    entries = history.load_history()
    print(f"\nFound {len(entries)} conversation sessions in history")

    if entries:
        print("\nMost recent sessions:")
        for entry in entries[:5]:
            timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M")
            project = Path(entry.project_path).name if entry.project_path else "No project"
            title = entry.title or "Untitled"
            print(f"  - {timestamp} | {project} | {title[:50]}")

    return entries


def test_recent_prompts():
    """Test getting recent prompts."""
    print("\n" + "=" * 60)
    print("TEST: Recent User Prompts")
    print("=" * 60)

    prompts = get_recent_prompts(limit=10)
    print(f"\nLast {len(prompts)} user prompts:")
    for i, prompt in enumerate(prompts, 1):
        # Truncate long prompts
        truncated = prompt[:100] + "..." if len(prompt) > 100 else prompt
        print(f"{i}. {truncated}")


def test_pattern_analysis():
    """Test pattern analysis."""
    print("\n" + "=" * 60)
    print("TEST: Pattern Analysis")
    print("=" * 60)

    history = ConversationHistory()
    sessions = history.get_recent_sessions(limit=20)

    print(f"\nAnalyzing {len(sessions)} recent sessions...")

    analyzer = PatternAnalyzer(sessions)

    # Find slash command candidates
    candidates = analyzer.find_slash_command_candidates(min_frequency=2)
    print(f"\nFound {len(candidates)} slash command candidates:")
    for cmd in candidates[:5]:
        print(f"\n  /{cmd.suggested_name} ({cmd.frequency} uses)")
        print(f"    {cmd.suggested_description}")
        print(f"    Example: {cmd.example_prompts[0][:80]}...")


def test_insights():
    """Test insight extraction."""
    print("\n" + "=" * 60)
    print("TEST: Insight Extraction")
    print("=" * 60)

    history = ConversationHistory()
    sessions = history.get_recent_sessions(limit=20)

    extractor = InsightExtractor(sessions)

    # Extract blockers
    blockers = extractor.extract_blockers()
    print(f"\nFound {len(blockers)} potential blockers:")
    for blocker in blockers[:3]:
        print(f"\n  {blocker.category.upper()}: {blocker.description}")
        print(f"    Frequency: {blocker.frequency}")
        if blocker.suggested_fix:
            print(f"    Fix: {blocker.suggested_fix}")

    # Extract best practices
    practices = extractor.extract_best_practices()
    print(f"\nFound {len(practices)} best practices:")
    for practice in practices[:3]:
        print(f"\n  {practice.title}")
        print(f"    Category: {practice.category}")
        print(f"    {practice.description[:100]}...")


def test_quick_report():
    """Test quick insights report."""
    print("\n" + "=" * 60)
    print("TEST: Quick Insights Report")
    print("=" * 60)

    report = quick_insights(limit=10)
    print("\n" + report)


def main():
    """Run all tests."""
    print("\nCONVERSATION INSIGHTS TEST SUITE")
    print("=" * 60)

    try:
        # Basic tests
        test_basic_parsing()
        test_recent_prompts()
        test_pattern_analysis()
        test_insights()
        test_quick_report()

        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("\nTo generate a full report:")
        print("  from conversation_insights import full_report")
        print("  output_path = full_report(limit=50)")
        print()

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
