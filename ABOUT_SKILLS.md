# What are Agent Skills?

Originally developed by Anthropic for Claude, Agent Skills are now an open standard adopted by multiple AI tools including GitHub Copilot.

Like MCP (Model Context Protocol), it's a way to extend LLM capabilities by providing specialized instructions and additional resources.

- **Official specification**: https://agentskills.io
- **VS Code Documentation**: https://code.visualstudio.com/docs/copilot/customization/agent-skills
- **Claude Code Documentation**: https://docs.anthropic.com/en/docs/claude-code/skills

## How does it work?

A skill is simply a folder containing a `SKILL.md` file with:
- Detailed instructions
- Scripts
- Examples
- Additional resources

The agent loads these skills dynamically and on-demand based on the conversation context.

See an example: https://agentskills.io/what-are-skills

## Why does it cost fewer tokens?

Unlike custom instructions or MCP tools that are always injected into the context, skills use a 3-level progressive loading system:

1. **Discovery**: Only the name and description (a few lines) are permanently loaded
2. **Instructions**: The SKILL.md content is only loaded when the skill is relevant
3. **Resources**: Additional files (scripts, examples) are only loaded when explicitly referenced

**Result**: You can have dozens of skills installed without wasting tokens. Only what's relevant to the current task gets loaded into context.

## Where to install skills?

Skills are placed in specific folders depending on your AI assistant:

| Assistant | Project Location | Global Location |
|-----------|------------------|-----------------|
| Claude Code | `.claude/skills/` | - |
| GitHub Copilot | `.github/skills/` | `~/.github/skills/` |
| Antigravity | `.agent/skills/` | `~/.gemini/antigravity/global_skills/` |

Enable in VS Code: `chat.useAgentSkills` (currently in preview)

## Where to find skills?

Many websites offer ready-to-use skills in the standard format:

- **Anthropic (official)**: https://github.com/anthropics/skills — Reference skills including document creation (docx, pdf, pptx, xlsx)
- **SkillsMP**: https://skillsmp.com — Community marketplace with 25,000+ skills
- **Smithery Skills**: https://smithery.ai/skills — 15,000+ community skills

## Build Your Own Skills

You can create custom skills tailored to your team's workflows!

### How to get started

- Follow the official specification: https://agentskills.io/specification
- VS Code guide: https://code.visualstudio.com/docs/copilot/customization/agent-skills#_create-a-skill
- Use Anthropic's skill-creator skill: https://github.com/anthropics/skills/tree/main/skills/skill-creator

### Example use cases for custom skills

- How to implement feature flags in your codebase
- How to run and write tests following your conventions
- How to document code/APIs according to your standards
- Deployment procedures and checklists
- Code review guidelines
- Setting up new projects with your boilerplate

**Basically, anything you find yourself explaining repeatedly to the team can become a skill!**
