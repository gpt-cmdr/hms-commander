# Claude Code Guide Reference Files

This directory contains cached copies of official Anthropic documentation for quick reference.

## Files

### skills-creation.md
Cached guidance from Anthropic's skills creation blog post. Includes:
- 5-step skills creation process
- Description requirements (CRITICAL for triggering)
- Naming conventions
- Testing strategies
- Best practices

**Source**: https://claude.com/blog/how-to-create-skills-key-steps-limitations-and-examples

### memory-system.md
Cached documentation on Claude Code's memory hierarchy. Includes:
- 4-level hierarchy (Enterprise, Project, Rules, User)
- Recursive loading pattern
- @imports syntax and usage
- Path-specific rules with YAML frontmatter
- Size recommendations

**Source**: https://code.claude.com/docs/en/memory

### official-docs.md
Links and WebFetch commands for official sources. Use this file to:
- Find official documentation URLs
- Get WebFetch commands to refresh cached content
- Locate additional Anthropic resources

## When to Use These Files

**Use cached files** for:
- Quick reference during development
- Verifying patterns and syntax
- Checking best practices

**Fetch live documentation** when:
- User explicitly requests latest docs
- Troubleshooting configuration issues
- Verifying specific technical details
- Cached content seems outdated

## Maintenance

These files should be periodically updated to reflect latest Anthropic guidance. The `claude-code-guide` agent can WebFetch fresh content and update these cached versions.
