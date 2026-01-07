Invoke the Code Oracle Codex subagent for deep code analysis using OpenAI's gpt-5.2-codex model.

Use this oracle for tasks requiring extended thinking (20-30 minutes):
- Architecture planning and design decisions
- Security audits and vulnerability analysis
- Complex refactoring strategies
- Multi-file impact analysis
- Pattern consistency analysis

The oracle uses HEREDOC syntax with codex-wrapper CLI. Always specify working directory as "C:/GH/hms-commander" for @file references.

Prerequisites: codex-cli plugin installed, OPENAI_API_KEY set or `codex login` completed.

Output location: `feature_dev_notes/Code_Oracle_Multi_LLM/reviews/` or `plans/`

Example invocation:
```bash
codex-wrapper - "C:/GH/hms-commander" <<'EOF'
Design basin model validation framework.

Context files:
@hms_commander/HmsBasin.py
@.claude/rules/hec-hms/basin-files.md

Requirements:
- Validate subbasin parameters
- Check connectivity
- Integration with static class pattern

Provide class structure and implementation plan.
EOF
```

See `.claude/agents/code-oracle-codex.md` for full documentation.
