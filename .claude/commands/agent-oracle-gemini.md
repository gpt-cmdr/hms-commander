Invoke the Code Oracle Gemini subagent for fast, large-context code analysis using Google's Gemini models.

Use this oracle for rapid analysis tasks (minutes, not hours):
- Large codebase scanning (10+ files)
- Pattern extraction and consistency checks
- Documentation completeness review
- Quick triage before deep analysis
- Multi-file pattern detection

Model selection via GEMINI_MODEL environment variable:
- `gemini-3-pro-preview` (default) - Standard quality
- `gemini-3-flash-preview` - Very large context (>100K tokens)

Prerequisites: gemini-cli plugin installed, GOOGLE_GENERATIVE_AI_API_KEY set.

Output location: `feature_dev_notes/Code_Oracle_Multi_LLM/surveys/` or `reviews/`

Example invocation:
```bash
export GEMINI_MODEL=gemini-3-pro-preview
uv run ~/.claude/skills/gemini/scripts/gemini.py \
  "Survey all static classes in hms_commander/ for @log_call decorator usage. Report patterns and inconsistencies." \
  "C:/GH/hms-commander"
```

See `.claude/agents/code-oracle-gemini.md` for full documentation.
