# Official Anthropic Documentation

This file contains links and WebFetch commands for official Anthropic documentation sources.

---

## Primary Documentation Sources

### 1. Skills Creation Blog Post

**URL**: https://claude.com/blog/how-to-create-skills-key-steps-limitations-and-examples

**Content**:
- 5-step skills creation process
- Description requirements (CRITICAL for triggering)
- Naming conventions (lowercase-with-hyphens)
- Testing and refinement strategies
- Best practices and examples

**Fetch Command**:
```
Use WebFetch tool with:
- url: https://claude.com/blog/how-to-create-skills-key-steps-limitations-and-examples
- prompt: Extract the 5-step skills creation process, description requirements, naming conventions, testing strategies, and all best practices. Focus on what makes descriptions trigger correctly and how to structure skill instructions.
```

**Cached Version**: `skills-creation.md`

---

### 2. Memory System Documentation

**URL**: https://code.claude.com/docs/en/memory

**Content**:
- 4-level memory hierarchy (Enterprise, Project, Rules, User)
- Recursive loading with @imports
- Path-specific rules using YAML frontmatter
- File organization best practices
- Size recommendations and token management

**Fetch Command**:
```
Use WebFetch tool with:
- url: https://code.claude.com/docs/en/memory
- prompt: Extract the complete memory hierarchy documentation including 4 levels, @imports syntax, recursive loading, path-specific rules with YAML frontmatter, file organization patterns, and size recommendations. Include all examples of proper usage.
```

**Cached Version**: `memory-system.md`

---

### 3. Claude Code Documentation Hub

**URL**: https://code.claude.com/docs

**Content**:
- General Claude Code features
- Configuration options
- Tool usage and best practices
- Integration patterns

**Fetch Command**:
```
Use WebFetch tool with:
- url: https://code.claude.com/docs
- prompt: Extract general Claude Code features, configuration options, and best practices. Focus on official recommendations for tool usage, project setup, and common workflows.
```

**Note**: This is a broader documentation hub. Fetch specific sections as needed.

---

## How to Use These Sources

### When to Fetch Live Documentation

**Fetch when**:
- User explicitly requests "latest" or "most recent" docs
- Troubleshooting configuration issues that may be version-specific
- Verifying specific technical details before providing guidance
- Cached content seems outdated or incomplete
- Anthropic may have updated guidance

**Examples of when to fetch**:
- User: "What's the latest guidance on skills creation?"
- User: "How does Claude Code handle memory now?"
- Agent: Troubleshooting a configuration issue and needs to verify current behavior

### When to Use Cached Files

**Use cached when**:
- Quick reference during normal development
- Providing standard guidance on established patterns
- User asks general "how to" questions
- Content is foundational and unlikely to change

**Examples of when to use cached**:
- User: "How do I write a skill description?"
- User: "What's the @import syntax?"
- Agent: Providing standard skills creation process

---

## WebFetch Examples

### Fetch Skills Guidance

```markdown
WebFetch: https://claude.com/blog/how-to-create-skills-key-steps-limitations-and-examples

Prompt: "Extract the 5-step skills creation process with emphasis on description requirements. Include all guidance on what makes descriptions trigger correctly, naming conventions, and testing strategies. Provide specific examples of good vs bad descriptions."
```

### Fetch Memory Documentation

```markdown
WebFetch: https://code.claude.com/docs/en/memory

Prompt: "Extract complete memory hierarchy documentation including all 4 levels, @imports syntax with examples, path-specific rules using YAML frontmatter, and size recommendations. Include all organizational patterns and best practices."
```

### Fetch General Claude Code Features

```markdown
WebFetch: https://code.claude.com/docs

Prompt: "Extract general Claude Code features, configuration best practices, and tool usage recommendations. Focus on official Anthropic guidance for project setup and workflows."
```

---

## Updating Cached Content

When official documentation is updated, refresh cached files:

1. **Fetch latest content** using WebFetch commands above
2. **Review changes** between cached and fetched content
3. **Update cached file** if significant changes exist
4. **Note update date** in cached file header

**Cached File Update Template**:
```markdown
# [Topic] Guide

**Source**: [URL]

**Last Updated**: YYYY-MM-DD (cached from Anthropic [source type])

**Changes from Previous Version**: [Brief summary of updates]

---

[Updated content]
```

---

## Additional Resources

### Anthropic Blog

**URL**: https://claude.com/blog

**Content**: Latest features, best practices, case studies

**Use for**: Discovering new Claude Code capabilities, understanding design decisions

### GitHub Discussions

**URL**: https://github.com/anthropics/anthropic-sdk-python/discussions

**Content**: Community questions, unofficial tips, edge cases

**Use for**: Troubleshooting unusual issues, community best practices

### Release Notes

**Check for**: Version-specific changes to memory system, skills, or configuration

**Use for**: Understanding breaking changes, new features, deprecated patterns

---

## Quick Reference

**Skills Blog**: https://claude.com/blog/how-to-create-skills-key-steps-limitations-and-examples
**Memory Docs**: https://code.claude.com/docs/en/memory
**Claude Code Hub**: https://code.claude.com/docs

**Fetch for**: Latest updates, troubleshooting, verification
**Use cached for**: Quick reference, standard patterns, general guidance

---

## Maintenance Schedule

**Recommended Review Frequency**:
- **Monthly**: Check for major documentation updates
- **Before major features**: Verify latest guidance before implementing new patterns
- **After Claude Code updates**: Review if significant version changes occur
- **When troubleshooting**: Fetch live docs to ensure current behavior

**Cached Files to Maintain**:
1. `skills-creation.md` - Core skills guidance
2. `memory-system.md` - Memory hierarchy and @imports
3. (Add additional cached docs as needed)
