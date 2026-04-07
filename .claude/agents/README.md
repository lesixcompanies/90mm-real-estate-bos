# Sub-Agents

Sub-agents are specialized workers that run in their own context window, can use different models, and return results to the main session. They keep your primary conversation clean while delegating specific tasks to the right tool at the right cost.

## Why Use Sub-Agents

- **Cost control** — Route research, bulk content, and simple lookups to Haiku instead of burning Opus tokens
- **Context preservation** — Research output stays in the sub-agent's window; only the summary returns to your main session
- **Specialization** — Each sub-agent has a focused system prompt for a specific type of work
- **Parallel work** — Multiple sub-agents can run simultaneously on different tasks

## Model Selection

| Model | Best For | Cost | Speed |
|-------|----------|------|-------|
| opus | Complex reasoning, diagnostics, change sequence work | Highest | Slowest |
| sonnet | Balanced work, content creation, analysis | Medium | Medium |
| haiku | Research summaries, bulk operations, simple lookups | Lowest | Fastest |

## How to Create a Sub-Agent

Create a markdown file in this directory (`.claude/agents/`) with YAML front matter:

```markdown
---
name: agent-name
description: When to use this agent — Claude reads this to decide when to delegate
model: haiku
tools:
  - Read
  - Write
  - Glob
  - Grep
---

You are a [role]. When invoked, [what you do].
[Specific instructions for how to complete the task.]
[Where to save output.]
```

### Required Fields
- `name` — Identifier for the agent
- `description` — When Claude should delegate to this agent. Write this clearly — Claude uses it to decide.

### Optional Fields
- `model` — `haiku`, `sonnet`, or `opus`. Defaults to your session model if not specified.
- `tools` — Restrict which tools the agent can use. Leave empty to allow all. Common tools: Read, Write, Glob, Grep, Bash.

## Connecting External Services (MCP)

Sub-agents can use MCP-connected tools. To connect Perplexity for research:

```
claude mcp add perplexity --env PERPLEXITY_API_KEY="your_key_here" -- npx -y @perplexity-ai/mcp-server
```

Your API key goes in your `.env` file. The MCP configuration is global — once added, any sub-agent (or the main session) can use Perplexity tools.

Other common MCP connections:
- Google Calendar, Gmail, Drive — available through Anthropic's built-in connectors
- Slack — MCP server available
- CRM systems — varies by provider; check if your CRM offers an MCP server

Once connected, reference the MCP tool in your sub-agent's tools list:

```yaml
tools:
  - Read
  - Write
  - mcp__perplexity
```

## Example: Research Agent on Haiku with Perplexity

```markdown
---
name: researcher
description: Performs web research and saves structured reports. Use when the system needs current information, market data, or competitive intelligence.
model: haiku
tools:
  - Read
  - Write
  - mcp__perplexity
---

You are a research agent. When invoked:
1. Use Perplexity to research the given topic
2. Gather information from multiple angles
3. Save a structured report to the appropriate folder:
   - Market research → references/
   - Competitive intelligence → references/
   - Topic research for content creation → references/
4. Return a 3-5 sentence summary to the main agent

Be thorough in sourcing but concise in summary. Include source URLs
in the full report. The main agent doesn't need the raw data — it
needs the conclusion and where to find the details.
```

## Example: Content Drafter on Haiku

```markdown
---
name: content-drafter
description: Drafts content in bulk. Use when multiple pieces of similar content are needed (e.g., 5 social media posts, a week of emails).
model: haiku
tools:
  - Read
  - Write
---

You are a content drafting agent. When invoked:
1. Read the relevant context files (context/me.md, context/market.md,
   and any brand documentation in references/)
2. Read the skill file for the content type being produced
3. Draft all requested pieces
4. Save drafts to the appropriate project folder
5. Return a summary of what was created to the main agent

Draft quality should be "good first draft" — the main agent or the
user will refine. Speed matters more than perfection at this stage.
```

## Best Practices

- **3-5 sub-agents maximum.** More than that and the system spends more time deciding which agent to use than actually working.
- **Start with one: a Haiku researcher with Perplexity.** That single agent handles the most common need — getting current information into the system without burning expensive tokens.
- **Match model to task, not to importance.** Haiku summarizing Perplexity research results produces output that's 90% as good as Opus at a fraction of the cost. Reserve Opus for complex reasoning, not information retrieval.
- **Sub-agents cannot spawn sub-agents.** This is a Claude Code limitation. Design your agents as single-task workers, not orchestrators.
- **Write clear descriptions.** Claude decides when to delegate based on the description field. Vague descriptions mean the agent never gets used or gets used for the wrong things.

## Integration with the Business Operating System

Sub-agents work alongside skills. A skill defines *what* to do (the process). A sub-agent defines *who does the work* (and at what cost). When the system invokes a skill that requires research, it can delegate the research step to the researcher sub-agent, then continue the skill's process with the results.

The S&T Tree may identify tasks where sub-agents would be valuable. When it does, the system can suggest creating one. The skill-builder (available in 90MM) can also create sub-agents when it detects a repeatable task that would benefit from model routing.

---
*Sub-agents are a Claude Code feature. See [Claude Code documentation](https://code.claude.com/docs/en/sub-agents) for the latest capabilities and configuration options.*
