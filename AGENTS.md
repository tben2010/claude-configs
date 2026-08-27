# AGENTS.md

This file provides guidance to AI coding agents (e.g. OpenAI Codex) when working with code in this repository.

**Important:** This repository contains configuration FOR Claude Code (claude.ai/code). All paths, file names, and concepts (`.claude-plugin/`, `.claude/settings.json`, `CLAUDE.md`, skills, MCP servers) are Claude Code conventions - do not rename them to match your own tooling. `CLAUDE.md` in the repo root carries the same guidance as this file, addressed to Claude Code; keep both in sync when updating either.

## Repository Purpose

This is a configuration repository for Claude Code plugins. It contains reusable plugin profiles that can be synced across multiple projects and computers via GitHub. The repository does not contain application code - it contains plugin configurations, skills, rules, agents, hooks, and MCP server configurations.

## Architecture

### Plugin System

This repository uses Claude Code's plugin architecture where:

1. **Plugin profiles** are self-contained directories with a `.claude-plugin/plugin.json` file
2. **Plugins are registered** in project `.claude/settings.json` files via `extraKnownMarketplaces` and `enabledPlugins`
3. **Multiple plugins can be composed** together in a single project
4. **Configuration is additive** - all plugins load together with project-specific settings

### Repository Structure

```
claude-configs/
├── profile-al-development/          # AL/Business Central development profile (v5.x)
│   ├── .claude-plugin/
│   │   ├── plugin.json              # Plugin metadata (name, version, agents list)
│   │   └── settings.json            # Plugin settings (enables agent teams)
│   ├── CLAUDE.md                    # Lead-as-Manager orchestration instructions
│   ├── skills/                      # 17 skills (workflow, build, knowledge)
│   │   └── <skill-name>/SKILL.md    # Each skill: frontmatter + instructions
│   ├── rules/                       # Auto-loaded AL coding rules
│   │   ├── al-engineering.md        # Always loaded
│   │   ├── al-architecture.md       # Loaded when *.al files in context
│   │   ├── al-conventions.md
│   │   ├── al-data-access.md
│   │   ├── al-naming.md
│   │   └── workflow-routing.md
│   ├── agents/                      # Subagents
│   │   └── al-repo-summarizer.md    # AL codebase overview agent
│   ├── hooks/                       # AL compile-on-turn-end hooks
│   │   ├── hooks.json.disabled      # Currently DISABLED (rename to enable)
│   │   ├── al-hook-compile.sh
│   │   └── al-hook-record.sh
│   ├── bc-code-intel-knowledge/     # BC Intelligence MCP knowledge base
│   │   ├── specialists/             # Specialist persona overrides
│   │   └── domains/                 # Domain knowledge
│   ├── .dev-templates/              # Templates for .dev/ task folders
│   ├── .mcp.json                    # MCP server configuration
│   ├── bc-code-intel-config.json    # BC Code Intelligence layer config
│   ├── bctb-config.json             # BC Telemetry Buddy config (host-local server)
│   └── README.md                    # Profile documentation
├── project-settings-template.json   # Template for project .claude/settings.json
├── CLAUDE.md                        # Same guidance, addressed to Claude Code
├── .gitignore
└── README.md                        # Repository overview and setup
```

Historical material (`CLAUDE.md.v2-backup`, `CLAUDE.md.v3-backup`, `.dev-v3-design.md`, design notes like `task-coordination.md`, `tdd-workflow.md`, `proportional-planning.md`) is kept in the profile root for reference but is not loaded by the plugin.

## Key Concepts (AL Profile v5.x)

### Lead-as-Manager Architecture

Since v3.0 (refined through v5.x), the AL profile no longer uses a fixed agent pipeline. Instead, the **main session acts as an engineering manager** that never writes code itself:

- **All work is delegated to subagents/teammates** - even trivial fixes - to preserve main-session context
- **Agent teams are enabled** via `.claude-plugin/settings.json` (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, `teammateMode: auto`)
- **Competitive solution design**: `/plan` spawns 2-3 architect agents that debate approaches before synthesis
- **Parallel implementation**: `/develop` spawns N developer agents on separate modules, then a 4-specialist review team (security, AL expert, performance, test coverage)
- **Parallel test development**: `/test` spawns 4 test engineers (unit, integration, scenario, edge case)

### Workflow Routing

Every user request is classified by complexity and routed to the matching skill:

| Complexity | Criteria | Route |
|------------|----------|-------|
| TRIVIAL | Single file, obvious fix | `/fix` |
| SIMPLE | 2-3 files, pattern exists | `/fix` or `/plan` → `/develop` |
| MEDIUM | 4-8 files, design decisions needed | `/plan` → `/develop` |
| COMPLEX | 9+ files, new architecture | `/interview` → `/plan` → `/develop` → `/test` |

### Document-Driven Development

- **Agents write results to files, return one-line summaries** - keeps the main conversation clean
- **Task folder convention**: all workflow output goes to `.dev/<task-slug>/` (e.g. `.dev/credit-limit-validation/01-requirements.md`); `.dev/project-context.md` is shared across tasks and initialized once via `/init-context`
- **User approval gates** between major phases (requirements → plan → implementation)

### Skills (replaced the former `commands/` directory)

Skills live in `skills/<name>/SKILL.md` with YAML frontmatter (`name`, `description`) and are user-invocable via `/<name>` or model-invoked:

- **Workflow**: `interview`, `plan`, `develop`, `fix`, `test`, `document`, `init-context`
- **Build/Run**: `compile`, `publish`, `run-tests`, `local-bc`, `al-symbols`
- **Test quality**: `al-mutate` (mutation testing), `verify-tests` (adversarial test verification)
- **Knowledge/Reference**: `bc-source` (BC base app source lookup), `build-tools`, `review-checklists`

### Rules (auto-loaded coding standards)

Rules in `rules/*.md` provide standing AL guardrails without skill invocation. Frontmatter controls loading: `al-engineering.md` is always loaded; rules with `globs: ["**/*.al"]` (naming, conventions, data access, architecture) load when AL files are in context. Coding standards belong in rules, not in skills or CLAUDE.md.

### Hooks (currently disabled)

`hooks/hooks.json.disabled` defines a PostToolUse recorder plus a Stop-hook that auto-compiles AL after each turn. It is deliberately disabled (rename to `hooks.json` to re-enable).

## MCP Server Integration

`.mcp.json` ships three portable servers:

1. **Microsoft Docs MCP** (`microsoft_docs_mcp`) - HTTP server for official AL/BC documentation
2. **AL Dependency MCP** (`al-mcp-server`) - base app object navigation, event discovery (via npx)
3. **BC Code Intelligence MCP** (`bc-code-intelligence-mcp`) - specialist consultations; runs via `npx -y bc-code-intelligence-mcp@latest`; custom layer config in `bc-code-intel-config.json` pointing at `bc-code-intel-knowledge/`

Two additional servers are **host-specific and intentionally NOT committed** (removed in c69ca94); they are added on machines where the tools are installed:

- **ALCOPS** (`alcops-mcp`, a .NET tool) - AL code analysis/fix rules
- **BC Telemetry Buddy** (`bctb-mcp`) - telemetry queries, configured via `bctb-config.json`

## Common Development Tasks

### Adding a New Plugin Profile

```bash
cd ~/Git/claude-configs
mkdir -p profile-name/{.claude-plugin,skills,agents,rules}

# Create plugin.json
cat > profile-name/.claude-plugin/plugin.json <<EOF
{
  "name": "profile-name",
  "description": "Brief description",
  "version": "1.0.0",
  "author": {
    "name": "Your Name"
  }
}
EOF

# Add configuration files
# - profile-name/CLAUDE.md
# - profile-name/skills/<skill>/SKILL.md
# - profile-name/agents/*.md
# - profile-name/.mcp.json (if needed)

git add profile-name/
git commit -m "Add profile-name plugin"
git push
```

### Creating a Skill

Skills are stored in `skills/<skill-name>/SKILL.md` (kebab-case) with frontmatter:

```markdown
---
name: skill-name
description: One-line description. Used for model-invocation matching.
---

# Skill Title

[Detailed instructions for Claude on how to execute this skill]
```

Supporting files (prompts, templates) live next to `SKILL.md` in the same directory.

### Creating an Agent

Agents are subagent definitions in `agents/*.md` with frontmatter (`name`, `description` with usage examples, optional `model`, `memory`), followed by the agent's system prompt. Register the agent in `plugin.json` under `"agents"`.

### Creating a Rule

Rules are markdown files in `rules/*.md`:

```markdown
---
description: What this rule covers
globs: ["**/*.al"]   # optional - omit to always load
---

# Rule content
```

### Testing Plugin Changes

```bash
# In a test AL project with the plugin enabled in .claude/settings.json
cd ~/path/to/test-project
claude

# Test a specific skill
/plan "test input"
```

Note: installed plugins are cached under `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`. After changing the repo, make sure the cache is updated (bump the version and/or reinstall/update the plugin) or the old copy keeps loading.

## Configuration Hierarchy

Claude Code loads configurations in this order (later overrides earlier):

1. Enterprise managed settings (if configured)
2. User settings (`~/.claude/settings.json`)
3. User plugins (registered in user settings)
4. **Project settings** (`.claude/settings.json`)
5. **Project plugins** (enabled in project settings) ← This repository's plugins load here
6. Local settings (`.claude/settings.local.json` - gitignored)

## File Naming Conventions

- **Skills**: `skills/skill-name/SKILL.md` (kebab-case directory)
- **Agents**: `agents/agent-name.md` (kebab-case)
- **Rules**: `rules/rule-name.md` (kebab-case)
- **Config**: `.claude-plugin/plugin.json`, `.claude-plugin/settings.json`, `.mcp.json`
- **Documentation**: `CLAUDE.md` (uppercase), `README.md`

## MCP Configuration Structure

MCP servers are configured in `.mcp.json` at the plugin root:

```json
{
  "mcpServers": {
    "server-name": {
      "type": "stdio|http|sse",
      "command": "executable",
      "args": ["arg1", "arg2"],
      "env": {
        "VAR_NAME": "value"
      }
    }
  }
}
```

Keep committed entries portable (npx, `~` paths). Host-specific servers (absolute paths, locally installed tools) belong only in the local machine's copy, not in git.

## Git Workflow

This repository is cloned to `~/Git/claude-configs/` and kept synchronized:

```bash
cd ~/Git/claude-configs
git pull  # Get updates from other computers
# ... make changes ...
git add .
git commit -m "Descriptive message"
git push  # Share with other computers
```

Remotes: `origin` is the user's fork; `upstream` points at the original community repo for periodic diffing.

## Security Considerations

- Never commit credentials, API keys, or certificates
- Use `.gitignore` to prevent accidental commits
- Keep authentication in project-local files (`.env`, gitignored)
- Keep host-specific absolute paths out of committed configs

## AL Profile Specifics

### Approval Gates

Workflows stop for user approval between major phases:

1. After requirements/interview - before solution planning
2. After solution planning - before implementation
3. After code review - before testing

`/fix` deliberately skips approval gates for fast iteration (3-tier classification instead).

### AL Compilation

Always use the `al-compile` wrapper (via the `/compile` skill) instead of manual AL compiler commands. It auto-detects the VS Code AL extension version, workspace structure, `.alpackages` directories, and ruleset files, and includes standard analyzers by default.

### Test Execution

- `al-runner` for fast pure-logic tests (no BC instance required)
- `bc-test` / `/run-tests` for integration tests against a running BC instance
- `/local-bc` manages a local BC instance (host vs container auto-detected)
- `/al-mutate` and `/verify-tests` prove test suites are meaningful

## Plugin Version Management

Plugins use semantic versioning in `plugin.json`:

- **Major**: Breaking changes (e.g., renamed skills, removed agents)
- **Minor**: New features (e.g., new skills, enhanced agents)
- **Patch**: Bug fixes, documentation improvements

Update the version in `plugin.json` and document changes in the profile's README.md.

## Troubleshooting

### Plugin Not Loading

1. Verify registration in project `.claude/settings.json`
2. Check `extraKnownMarketplaces` path is absolute
3. Validate `plugin.json` syntax
4. Run `/config` in Claude Code to see loaded plugins

### MCP Server Issues

1. Check `.mcp.json` syntax
2. Verify executable paths (e.g., `npx`, `alcops-mcp` in PATH)
3. Test MCP servers independently
4. Check environment variables are set correctly

### Skill Not Found

1. Ensure plugin is enabled in project settings
2. Skill must be at `skills/<name>/SKILL.md` with valid frontmatter
3. Skill names are kebab-case
4. Restart the Claude Code session if needed

### Changes Not Appearing

1. Settings and CLAUDE.md hot-reload automatically
2. For skill/agent changes, start a new Claude Code session
3. Verify changes are committed and pushed; on other computers run `git pull`
4. Check the plugin cache (`~/.claude/plugins/cache/`) isn't serving a stale version

## Best Practices

1. **Test before pushing** - Verify changes work in a test project
2. **Clear commit messages** - Describe what changed and why
3. **Update documentation** - Keep READMEs, CLAUDE.md, and this file in sync
4. **Semantic versioning** - Increment version in plugin.json
5. **Backward compatibility** - Avoid breaking changes when possible
6. **Scope plugins narrowly** - One technology/domain per plugin
7. **Standards in rules, orchestration in CLAUDE.md, workflows in skills** - keep concerns separated
8. **Use approval gates** - Stop for user validation at major decision points
