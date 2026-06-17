---
name: intent-router
description: Use when the user asks which skill, plugin, connector, app, tool, or workflow to use; asks to route, triage, auto-select, or recommend capabilities; or when multiple installed capability families could materially change the first action. Also use after the agent participates in skill install/update/rule changes or explicit removal/disable requests to keep the route map current. Do not trigger merely because a task is non-trivial.
---

# Intent Router

Route user intent to the smallest useful skill, plugin, connector, app/tool route, or direct workflow. Do not make users memorize skill names. Treat each request like a tiny RAG query: understand the query, retrieve candidate routes, check evidence, rerank, expose a short routing note, and then recommend or execute according to the user's intent.

## Scope And Limits

This router is a customizable global routing map for the current user's installed skills, plugins, connectors, app tools, and direct workflows.

It is not a background filesystem watcher, mandatory middleware, or universal plugin caller. It cannot notice external manual edits to a skill directory unless the user tells the agent, the agent performs the install/update/delete, or an inventory refresh runs during the task.

New or changed skills may require a session restart or skill inventory refresh before they appear in the active skill list. The route map can still record the intended route and caveat.

## Safety Gate

If the user says "read-only", "review", "do not edit", "recommend only", "no file changes", or asks for critique only, do not install, sync, edit, stage, commit, write files, call paid APIs, deploy, publish, share, send messages, write external state, or delete data. Treat changes as recommendations unless the user later asks to apply them.

If the user names a skill:

- If the skill is the requested workflow, use that skill first.
- If the skill is the target artifact being reviewed, edited, compared, installed, or explained, inspect it as the object of the task instead of activating it as the workflow.
- If the user names this router while asking to do another task, treat the router as the meta-pass only. Do not select the router itself as the terminal primary route unless the task is router maintenance, router review, route recommendation, eval, install/update/delete/disable sync, or explaining routing itself.

## Cost And External Side-Effect Gate

Before using a route that may spend money, consume paid quota, create API keys, call a metered API, deploy, publish, share externally, send messages or email, write calendar events, create automations, mutate cloud data, or delete data, state the likely side effect and get approval unless all of these are already clear:

- exact target or account
- scope and rough cost or quota risk when cheaply knowable
- production vs preview, public vs private destination
- whether the action writes external state

Having an API key configured is not approval to spend quota. Never ask users to paste secrets in chat when a secure setup flow exists.

If the user explicitly asks for an external action, treat that as approval of the intent, but still confirm missing target/account/environment details or production/public/cost risks.

## Plugin And Connector Preflight

Route across four capability types:

- local skill: open the selected skill's `SKILL.md`
- plugin skill: open the plugin skill and use its plugin-specific guidance
- app, connector, or tool route: use the callable tool when it is available in the current session
- direct route: proceed with normal agent tools when no dedicated skill or plugin fits

When a plugin or connector is likely relevant, check whether it is currently callable. If tool discovery is available, search for the plugin/tool before falling back.

If the needed plugin is not callable, do not pretend it was used. Recommend it, or request installation only when the user explicitly asks for that exact known installable plugin or connector.

## First Move

1. If the user asks only "which skill/plugin/tool should I use?", run Guided Recommendation Mode.
2. If the user names this router as the workflow, run the RAG-style routing loop below, then choose the downstream route that should actually do the work.
3. If the user names a skill as the requested workflow, use that skill first. If the skill is the object under review/edit/install/explanation, inspect it as the object.
4. If the agent installs, updates, modifies, configures, or accepts a skill source in this turn, run the Router Sync Protocol before the final answer. If the task is read-only, report what sync would change instead of editing.
5. If the user explicitly asks to delete, remove, disable, or stop recommending a skill, verify the exact target and intent before destructive changes. Then update the route map if state changed.
6. If several skill, plugin, connector, or direct workflow families would materially change the first action, choose 1 downstream primary route and at most 2 secondary routes from `references/skill-map.md`.
7. Before choosing a domain/action route, run the Upstream Discovery Gate below. If it fires, choose a brainstorming/design/intake/requirements route first, with domain/action routes as secondary follow-ons.
8. If a route uses plugins/connectors/apps/tools, run Plugin And Connector Preflight.
9. If a route may spend quota or mutate external state, run Cost And External Side-Effect Gate.
10. After choosing an installed primary skill, open that skill's `SKILL.md` before applying it. The map decides what to open first; it never replaces the primary skill body.
11. If the task is trivial, answer directly with a short no-skill clause.

Default route line:

```markdown
I will use <primary-skill/direct-route> because <trigger evidence + first action>.
```

## RAG-Style Routing Loop

Use this loop silently before answering or acting:

1. Query understanding: extract useful Query Facets.
2. Candidate retrieval: pull 2-5 plausible skills, plugin routes, connector routes, or direct routes from `references/skill-map.md`.
3. Evidence check: match concrete trigger phrases, requested output format, dependencies, caveats, and overlap notes. Reject candidates with weak evidence.
4. Rerank: choose exactly one primary route and at most two secondary routes. Prefer output surface first, then workflow risk, then tool dependency.
5. Threshold: ask one funnel question only when the Question Gate says to ask.
6. Answer synthesis: state the primary route, include the first observable action, then recommend or execute.
7. Feedback loop: if the route fails, classify why and update eval/map only when write scope allows it.

Only show secondary routes when they change the action, and explain their role or trigger condition. Do not expose the whole skill library.

### Upstream Discovery Gate

Choose an upstream thinking/design route before search, implementation, brokerage, deployment, scheduling, or automation when the request is broad, emotionally negative, multi-system, or high-risk.

Use a brainstorming, project-intake, or requirements-clarifier route as primary when the user asks to rethink, rebuild, redesign, personalize, research alternatives, adapt another project, confirm direction, create an evolvable/verifiable system, or combine current research with implementation/automation. Common cues include "this is terrible", "redo it", "search again", "build on someone else's project", "personalized", "verifiable", "iterative", "evolving system", "core requirement", "direction", "forward-looking", "scheduled purchase", and "create a recurring task".

First action: inspect the smallest relevant context, then ask one clarifying question about purpose, constraints, success criteria, risk boundary, and validation loop. Do not jump straight to solution search, code, live trading, deployment, or scheduling.

Use an implementation route only when the requirement is already clear or the user explicitly says to skip clarification. Use domain/action routes as secondary follow-ons after the design direction is approved.

## User-Visible Routing Note

For every non-trivial routed turn, briefly expose the routing process. This is a contract, not optional polish.

The note must include:

- the user cue or facet that triggered routing
- 2-3 candidates considered, unless the task is trivial
- the chosen primary route and why it wins
- any auxiliary or backup route and when it matters
- at least one rejected candidate and why it was not used
- the next observable action

Format:

```markdown
Routing note: detected <user cue>; candidates were <A>, <B>, <direct route>; selected <primary/direct> because <positive evidence>; did not use <candidate> because <negative evidence>; next step: <first observable action>.
```

If no dedicated skill is used:

```markdown
No dedicated skill is needed because <reason>. Candidate <A>/<B> were not used because <anti-cue or mismatch>. I will directly <first action>.
```

For trivial one-step tasks:

```markdown
No skill needed; this is a direct one-step answer.
```

## Query Facets

Extract only what is useful:

| Facet | Look For |
|---|---|
| intent | recommend, execute, explain, learn, install/update/delete/disable, review |
| output surface | code, UI, docx, pptx, PDF, spreadsheet, note, wiki page, image, automation |
| domain | repo/framework, academic, travel, admissions, calendar, macOS, OpenAI docs, RAG |
| capability type | local skill, plugin skill, app connector, MCP/tool route, direct route |
| risk | file writes, destructive action, high-stakes advice, current facts, privacy, external dependency, paid quota, external side effect |
| learning mode | "teach me", "do not code yet", one-question-at-a-time, quiz/checkpoint |
| write scope | no write, scratch artifact, skill file, repo file, personal vault, calendar, automation |
| dependency | API key, CLI, browser, connector, plugin, live app, local path, network/current source |

Facet priority when signals conflict:

`safety/write scope > learning/read-only/current-fact risk > intent/collaboration mode > output surface > domain > dependency > preference`

Examples: read-only beats sync, learning mode beats implementation, explicit `.docx` beats polished-PDF instincts, current model/pricing questions beat memory.

## Candidate Evidence Card

Keep this mentally for any non-trivial route. Make it explicit when explaining a route, debugging a route, or updating eval cases:

```markdown
candidate:
facet_summary:
matched cue:
map evidence:
positive evidence:
negative evidence:
dependency caveat:
first action:
score_breakdown:
threshold_decision:
```

## Rerank Rubric

Score close candidates 0-2 on each factor:

| Factor | Meaning |
|---|---|
| trigger match | Does the user's wording match the route trigger? |
| output match | Does the route produce or edit the requested output surface? |
| domain fit | Is the route meant for the repo/tool/domain? |
| risk fit | Does the workflow handle the failure/risk mode? |
| dependency fit | Are required tools/paths likely available or cheap to verify? |
| collaboration fit | Does it match recommend vs execute vs learning mode? |

Subtract 2 for a strong anti-cue, such as choosing an implementation route when the user says "recommend only" or choosing a PDF route when editable `.pptx` is explicit.

Threshold:

- top route score >= 8 and margin >= 2: route directly
- margin < 2: use the relevant ambiguity rule or ask one funnel question
- missing output surface, target platform, write scope, or location where a wrong choice would touch files: ask one funnel question
- trivial task: answer directly with the short no-skill clause

Keep numeric scores mental unless the user asks why, a route fails, or eval cases are being updated.

## Question Gate

Ask a funnel question only when all are true:

1. Two plausible routes would produce different first actions.
2. Cheap inspection cannot resolve the route.
3. A wrong route would waste time, spend money, touch files, or confuse learning mode.

Otherwise state the assumption and proceed.

## Guided Recommendation Mode

Use when the user is unsure where to start, asks "which skill should I use?", or asks for skill/plugin recommendations rather than direct execution.

Ask at most one missing question before recommending, unless the user explicitly asks for a longer interview. Skip anything already clear from context.

1. Broad area:
   - coding/building
   - debugging/broken behavior
   - design/UI/creative output
   - documents/slides/PDF/spreadsheets
   - knowledge/notes/wiki
   - research/current information
   - deployment/git/automation
   - skill authoring/router maintenance
2. Specificity:
   - clear spec
   - rough idea
   - starting from scratch
3. Domain or stack, only if relevant.
4. Collaboration mode, only if unclear: direct execution, collaborative checkpoints, or recommendation only.

Then answer:

```markdown
Primary: `<skill-name>` - why this is the best first skill.
Also consider:
- `<skill-2>` - when to layer it in.
- `<skill-3>` - when to layer it in.
Invoke like:
`Use <skill-name> to <user goal>`
```

Offer a ready prompt only when the user is choosing a workflow manually. If the user asked the agent to handle the task, proceed after naming the selected route.

## Router Sync Protocol

Run this when the agent participates in installing, updating, modifying, configuring, accepting, deleting, disabling, or rejecting a skill source. The user should not need to separately say "sync the router" after a successful skill change.

Read-only guard: if the user explicitly asks for only review, inspection, evaluation, or no file changes, do not edit the map. Report whether sync would be needed and what would change.

1. Inspect the new or changed `SKILL.md` frontmatter and README if present.
2. Update `references/skill-map.md` with:
   - skill name, source/path, and one-line purpose
   - trigger phrases the user would naturally say
   - overlaps with similar skills and when to choose it instead
   - dependencies, caveats, stale paths, or restart requirements
   - plugin/connector/tool dependencies if the route needs one
   - cost or external side-effect gates if relevant
3. If a skill was updated or its rules changed, update affected route cards and add or adjust eval cases.
4. If the user says a skill should no longer be recommended but did not explicitly ask to delete files, demote or hold the route; do not delete.
5. If the user explicitly asks to delete/remove a skill, verify exact name, absolute path, and delete scope before destructive action.
6. If the source is not installed because it is not a real skill, add a short hold note only if it prevents future confusion.
7. In the final answer, mention whether the router map changed and whether restart/inventory refresh may be needed.

Use `bash scripts/list-installed-skills.sh` to refresh raw inventory when needed.

## Routing Feedback Protocol

Run this whenever the user corrects the route, a chosen route fails for avoidable reasons, or a new natural phrase appears:

1. Identify the missed cue, wrong candidate, missing caveat, or unnecessary question.
2. Classify the failure as one of: `facet_miss`, `retrieval_miss`, `evidence_miss`, `rerank_miss`, `threshold_miss`, `dependency_miss`, `plugin_callability_miss`, `cost_gate_miss`, `external_side_effect_miss`, `mode_miss`, `map_stale`, `tool_name_stale`.
3. Add or update an eval case in `references/router-eval-cases.md`.
4. Update `references/skill-map.md` only if the failure came from a missing trigger, overlap rule, caveat, stale tool name, or recurring workflow.
5. Re-run affected eval cases mentally, manually, or with subagent review before finalizing.

If the turn is read-only, do not update eval or map files. Report the exact eval/map changes that should be made.

## Routing Discipline

- Prefer the narrowest route that matches the immediate need.
- Prefer 1-3 routes, not a giant chain.
- Recommend exactly one primary route and at most two secondary routes.
- If the goal spans categories, choose the most upstream useful route first: clarify/spec before build, reproduce before fix, source-check before framework code, file-format skill before visual polish.
- Do not dump the full skill list.
- When routes overlap, choose by output surface first, then workflow risk, then tool dependency.
- Name the first observable action.
- Verify stale personal paths before using them.
- Verify dependency-heavy routes when cheap before relying on them.
- For current facts, prices, docs, laws, schedules, models, libraries, or recommendations, use current/official sources instead of memory.
- In learning mode, do not jump into implementation unless the user explicitly switches modes.
- If a request mentions RAG, routing, retrieval, evidence, rerank, or eval, separate the stages.

## Self-Check Before Final Answer

Silently verify:

- Did I show the visible routing note for non-trivial routed turns?
- Did I choose one primary route?
- Did I use at most two secondary routes?
- Did I explain why the primary route was selected?
- Did I explain why visible rejected candidates were not used?
- Did I distinguish recommendation from execution?
- Did I treat a named skill correctly as workflow vs artifact?
- Did I avoid unnecessary questions?
- Did I open the primary skill's `SKILL.md` before applying it?
- Did I respect read-only/no-edit instructions?
- Did I state the first observable action?
- Did I preflight plugin/connector/tool availability before claiming use?
- Did I get approval for paid quota or external side effects when required?
- Did I verify current facts with current/official sources when required?
- Did I mention sync status if skills changed?
