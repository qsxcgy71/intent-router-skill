# Intent Router Skill

An installable agent skill for routing user intent to the right skill, plugin, connector, app tool, or direct workflow.

It is meant for people who have a growing skill library and do not want to memorize every skill name. The router treats each request like a small RAG query: understand the intent, retrieve candidate routes, check evidence, rerank, explain the route, and then recommend or execute.

## Why This Exists

Large skill libraries fail in a predictable way: users install many useful tools, then forget which one to call. A router skill becomes useful only if it is specific enough to choose well, but generic enough that other people can safely customize it.

This public version is designed to avoid common adoption failures:

- No personal paths, accounts, or private project names in the default map.
- Clear installation and customization steps.
- A visible routing note so users know why a route was chosen.
- Cost, quota, deployment, sharing, deletion, and cloud-write gates.
- Plugin and connector preflight instead of pretending unavailable tools were used.
- A small golden-case eval file that maintainers can review manually or with subagents.
- A route map that users are expected to edit for their own installed skills.

See [references/failure-checklist.md](references/failure-checklist.md) for the full audience failure checklist.

## Attribution

This project uses the public `skill-router` concept listed on EliteAI.tools as a reference:

- EliteAI.tools page: https://eliteai.tools/agent-skills/skill-router
- Referenced source shown there: `sickn33/antigravity-awesome-skills/skills/skill-router`

The referenced skill focuses on interviewing a user and recommending one primary skill plus up to two secondary skills. This project adapts that idea into a more configurable router with evidence checks, reranking, visible route notes, plugin/tool preflight, safety gates, and maintenance rules.

## Install

Install into your Codex skills directory:

```bash
mkdir -p ~/.codex/skills/intent-router
cp -R SKILL.md references scripts ~/.codex/skills/intent-router/
```

Then restart or refresh your agent session so the new skill appears in the active skill list.

If you use a skill installer that supports GitHub repositories, install this repository root as the skill source because `SKILL.md` is at the repo root.

## Configure

1. Run the inventory helper:

```bash
bash ~/.codex/skills/intent-router/scripts/list-installed-skills.sh
```

2. Edit:

```text
~/.codex/skills/intent-router/references/skill-map.md
```

3. Replace the starter route cards with the skill names, plugins, connectors, and direct workflows actually available in your environment.

4. Add or update golden cases in:

```text
~/.codex/skills/intent-router/references/router-eval-cases.md
```

5. Restart or refresh the agent session if newly installed skills do not appear.

## Example Invocation

```text
Use intent-router to decide which skill/plugin/tool should handle this.
```

```text
I do not know which skill to use. I want to turn a rough app idea into an implementation plan.
```

```text
Route this request, but only recommend. Do not execute anything yet.
```

## Expected Output Shape

For non-trivial routed requests, the skill should expose a short route note:

```markdown
Routing note: detected <user cue>; candidates were <A>, <B>, <direct route>; selected <primary> because <evidence>; did not use <candidate> because <negative evidence>; next step: <first observable action>.
```

Then it should name one primary route and at most two auxiliary routes.

## What This Skill Does Not Do

- It is not a background filesystem watcher.
- It cannot notice external edits to your skill directory unless your agent sees the change or you refresh inventory.
- It does not guarantee a plugin or connector is callable in the current session.
- It should not spend paid quota, deploy, publish, send messages, write external data, create API keys, or delete data without a gate.
- It is not a replacement for the selected skill's own `SKILL.md`.

## Repository Contents

```text
SKILL.md
references/
  failure-checklist.md
  router-eval-cases.md
  skill-map.md
scripts/
  list-installed-skills.sh
```

## Maintenance Pattern

When you install, update, disable, or remove skills, update `references/skill-map.md` and add eval cases for the changed routing behavior. The router can remind the agent to do this, but it is not a daemon and cannot enforce changes made outside the current session.

## License

MIT. See [LICENSE](LICENSE).
