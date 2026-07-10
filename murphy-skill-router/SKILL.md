---
name: murphy-skill-router
description: Use when Murphy explicitly asks which skill, plugin, connector, app, tool, or workflow to use, says "自动判断", "帮我分诊", "按合适的 skill/plugin", or when multiple installed skill/plugin families could materially change the next action. Also use automatically after Codex participates in skill install/update/rule changes or explicit removal/disable requests to sync the global map. Do not trigger merely because a task is non-trivial.
---

# Murphy Skill Router

Lightweight global router for Murphy's installed skills, plugins, connectors, apps, and direct tool routes. Do not make Murphy memorize names. Treat each user request like a tiny RAG query: retrieve candidate routes, cite the matching trigger evidence, rerank to the smallest useful set, then recommend or execute.

## Global Scope And Limits

This router is Murphy's global personal routing map because it lives under `~/.codex/skills`, not inside one project. Apply it across workspaces unless a route card is explicitly repo-specific.

It is not a background filesystem watcher or mandatory middleware. It cannot notice external manual edits to `~/.codex/skills` unless Murphy tells Codex, Codex performs the install/update/delete, or an inventory refresh is run during a Codex task.

New or changed skills may require a Codex restart or skill inventory refresh before they appear in the active skill list. The map can still record the intended route and caveat.

## Safety Gate

If Murphy says "只读", "review", "不要改文件", or asks for critique only, do not install, sync, edit, stage, commit, or write files. Treat changes as recommendations unless Murphy later asks to apply them. Treat "评估" as read-only only when Murphy has not also asked to apply changes.

If Murphy names a skill:

- If the skill is the requested workflow, use it first.
- If the skill is the target artifact being reviewed, edited, compared, installed, or explained, inspect it as the object of the task instead of activating it as the workflow.
- If Murphy names `murphy-skill-router` while asking to do another task, treat the router as the meta-pass only. Do not select `murphy-skill-router` as terminal primary unless the task is router maintenance, router review, route recommendation, eval, install/update/delete/disable sync, or explaining routing itself.

## Cost And External Side-Effect Gate

Before using any route that may spend money, consume paid quota, create API keys, call a metered API, deploy, publish, share externally, send messages/email, write calendar events, create automations, mutate cloud data, or delete data, state the likely side effect and get Murphy's approval unless all of these are already clear in the current turn:

- exact target or account
- scope and rough cost/quota risk when cheaply knowable
- production vs preview/public vs private destination
- whether the action writes external state

Having an API key configured is not approval to spend quota. For OpenAI API work, use secure key setup flows when keys are needed, never ask Murphy to paste secrets in chat, and ask for approval before the first paid or quota-consuming call in a task.

If Murphy explicitly asks for an external action like deployment, treat that as approval of the intent, but still confirm missing target/account/env details or any production/public/cost risk.

## Plugin And Connector Preflight

Route across four capability types:

- local skill: open the selected skill's `SKILL.md`
- plugin skill: open the plugin skill and use its plugin-specific guidance
- app/connector/tool route: use the callable tool when it is available in this session
- direct route: execute with normal Codex tools when no dedicated skill/plugin fits

When a plugin or connector is likely relevant, check whether it is currently callable. If the tool is not visible and `tool_search` is available, search for the plugin/tool before falling back.

If the needed plugin is not callable, do not pretend it was used. Recommend it, or request installation only when Murphy explicitly asks for that exact plugin/connector and it is in the known installable list. If the user only asks "what plugin should I use?", recommend; do not install.

## First Move

1. If Codex installs, updates, modifies, configures, or accepts a skill source in this turn, run the **Router Sync Protocol** before the final answer. Murphy does not need to separately say "同步 router". If the task is read-only, report what sync would change instead of editing.
2. If Murphy asks only "which skill should I use?", run **Guided Recommendation Mode**.
3. If Murphy names a skill as the requested workflow, use that skill first; if the skill is the object being reviewed/edited/installed/explained, inspect it as the object.
4. If Murphy explicitly asks to delete, remove, disable, or stop recommending a skill, verify the exact target and intent before destructive changes; then sync the router map if state changed.
5. If Murphy asks for auto-routing, plugin routing, or several skill/plugin families would materially change the first action, choose 1-3 downstream routes from `references/skill-map.md`. Keep `murphy-skill-router` visible as a candidate, but do not let it crowd out the downstream primary route.
6. Before choosing a domain/action route, run the **Upstream Discovery Gate** below. If it fires, choose `superpowers:brainstorming` or the narrow clarifier first, with domain/action routes as secondary follow-ons.
7. If a route uses plugins/connectors/apps/tools, run the **Plugin And Connector Preflight**.
8. If a route may spend quota or mutate external state, run the **Cost And External Side-Effect Gate**.
9. After choosing an installed primary skill, open that skill's `SKILL.md` before using it. The map decides what to open first; it never replaces the primary skill body. Direct routes and app/tool routes may not have a local skill body.
10. If the task is trivial, answer directly with the short no-skill clause.

Say: `我会用 X，因为 Y。`

## RAG-Style Routing Loop

Use this loop silently before answering or acting:

1. **Query understanding:** extract the Query Facets below.
2. **Candidate retrieval:** pull 2-5 plausible skills or direct-execution routes from `references/skill-map.md`; include Murphy recurring workflows when relevant.
3. **Evidence check:** for each candidate, match concrete trigger phrases, output format, dependencies, and overlap notes. Reject candidates with weak evidence.
4. **Rerank:** choose exactly one primary route and at most two secondary routes. Prefer output surface first, then workflow risk, then tool dependency.
5. **Threshold:** use the Question Gate below before asking anything.
6. **Answer synthesis:** state the primary route in one sentence, include the first observable action, then recommend or execute.
7. **Feedback loop:** if the route fails, record the failure mode mentally and use the closest ambiguity rule or dependency preflight before retrying.

### Upstream Discovery Gate

Choose an upstream thinking/design route before search, implementation, brokerage, deployment, or automation when the request is broad, emotionally negative, multi-system, or high-risk.

Use `superpowers:brainstorming` as primary when Murphy asks to rethink, rebuild, redesign, personalize, research alternatives, adapt another project, confirm direction, create an evolvable/verifiable system, or combine current research with implementation/automation. Common cues include "垃圾", "重做", "重新搜索", "别人项目基础上", "个性化", "可验证", "可迭代", "进化", "核心需求", "修改方向", "前瞻性", "预定时间", and "定时任务". First action: inspect the smallest project context, then ask one clarifying question about purpose/constraints/success criteria. Do not jump straight to solution search, code, live trading, deployment, or scheduling.

Use `quick-requirement-clarifier` instead when the user describes a small existing-repo change that is fuzzy but close to implementable. Use `project-intake-interview` when the user is starting a new project from scratch and asks for intake. Use implementation routes only when the requirement is already clear or Murphy explicitly says to skip clarification.

For trading/finance system requests, this gate is extra important: `Public Equity Investing`, `futuapi`, and Automations can be secondary, but the first route should clarify the strategy, risk boundary, data sources, validation loop, trading frequency, and whether any action could become real-money or external-state mutation.

Output route card:

```markdown
我会用 <primary-skill/direct-route>，因为 <trigger evidence + first action>。
```

Only show secondary skills when they change the action, and explain the role or trigger condition for each one. Do not expose the whole skill library or a long candidate list.

### User-Visible Routing Note

For every routed turn, briefly expose the routing process. This is a contract, not optional polish. Do not dump the full skill library; show only the top 2-3 relevant candidates.

The note must include:

- the user cue or facet that triggered routing
- 2-3 candidates considered
- `murphy-skill-router` as one visible candidate in every routed turn; phrase it exactly as `候选为 murphy-skill-router, <A>, <B>` or equivalent
- the chosen primary skill or direct route and why it wins
- any auxiliary/backup skill and when it would matter
- at least one rejected candidate and why it was not used
- the next observable action

Format:

```markdown
分诊过程：识别到 <user cue>; 候选为 murphy-skill-router, <A>, <B>; 选择 <primary/direct>，因为 <positive evidence>; 未用 <candidate>，因为 <negative evidence>; 下一步 <first observable action>。
```

If using skills:

```markdown
主 skill: <skill> — <why selected>.
辅助/备选: <skill> — <why included or when it would be used>.
```

If not using a dedicated skill:

```markdown
不调用专门 skill，因为 <reason>. 候选 <A>/<B> 没用的原因分别是 <anti-cue or mismatch>. 我会直接 <first action>.
```

For trivial one-step tasks, the note may be one short clause, but still name `murphy-skill-router` as a candidate:

```markdown
不调用专门 skill，因为这是一次性直接回答；候选为 murphy-skill-router, direct-route；我会直接给结果。
```

### Query Facets

Extract only what is useful; do not show this unless explaining a routing mistake.

| Facet | Look For |
|---|---|
| intent | recommend, execute, explain, learn, install/update/delete/disable, review |
| output surface | code, UI, docx, pptx, PDF, spreadsheet, Obsidian note, WiKi page, image, automation |
| domain | repo/framework, academic, travel/shopping, admissions, calendar, macOS, OpenAI docs, RAG |
| capability type | local skill, plugin skill, app connector, MCP/tool route, direct route |
| risk | file writes, destructive action, high-stakes advice, current facts, privacy, external dependency, paid quota, external side effect |
| learning mode | "先不要写代码", "按昨天节奏", one-question-at-a-time, quiz/checkpoint |
| write scope | no write, scratch artifact, skill file, repo file, personal vault, calendar/automation |
| dependency | API key, CLI, browser, connector, plugin, live app, local path, network/current source |

Facet priority when signals conflict:

`safety/write scope > learning/read-only/current-fact risk > intent/collaboration mode > output surface > domain > dependency > preference`

Examples: read-only beats sync, learning mode beats implementation, explicit `.docx` beats polished-PDF instincts, current model/pricing questions beat memory.

### Candidate Evidence Card

Keep this mentally for any non-trivial route; make it explicit when explaining a route, debugging a route, or updating eval cases:

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

If Murphy asks why a route was chosen, summarize the card instead of giving a generic category label.

### Rerank Rubric

Score close candidates 0-2 on each factor:

| Factor | Meaning |
|---|---|
| trigger match | Does the user's wording match the skill trigger? |
| output match | Does the skill produce or edit the requested output surface? |
| domain fit | Is this skill meant for the repo/tool/domain? |
| risk fit | Does the workflow handle the failure/risk mode? |
| dependency fit | Are required tools/paths likely available or cheap to verify? |
| collaboration fit | Does it match recommend vs execute vs learning mode? |

Subtract 2 for a strong anti-cue, such as choosing `kami` when editable `.pptx` is required or choosing implementation when Murphy says "先不要写代码".

Threshold:

- top route score >= 8 and margin >= 2: route directly
- margin < 2: use the relevant ambiguity rule or ask one funnel question
- missing output surface, target platform, write scope, or location where wrong choice would touch files: ask one funnel question
- trivial task: answer directly with the short no-skill clause

For any non-trivial route, expose a short candidate/choice/rejected-candidate explanation. Keep numeric score, exact margin, and detailed threshold reasoning mental unless Murphy asks why, a route fails, or eval cases are being updated.

### Question Gate

Ask a funnel question only when all are true:

1. Two plausible routes would produce different first actions.
2. Cheap inspection cannot resolve the route.
3. A wrong route would waste time, spend money, touch files, or confuse learning mode.

Otherwise state the assumption and proceed.

## Guided Recommendation Mode

Use when Murphy is unsure where to start, asks "用什么 skill", or asks for skill recommendations rather than direct execution.

Ask at most one missing question before recommending, unless Murphy explicitly asks for a longer interview. Skip anything already clear from context.

1. Broad area:
   - coding/building
   - debugging/broken behavior
   - design/UI/creative output
   - documents/slides/PDF/spreadsheets
   - knowledge/notes/wiki/Obsidian
   - research/current information
   - deployment/git/automation
   - skill authoring/router maintenance
2. Specificity:
   - clear spec
   - rough idea
   - starting from scratch
3. Domain or stack, only if relevant: framework, repo, file type, platform, tool, or target output.
4. Collaboration mode, only if unclear: direct execution, collaborative checkpoints, or recommendation only.

Then answer with this compact structure:

```markdown
Primary: `<skill-name>` — why this is the best first skill.
Also consider:
- `<skill-2>` — when to layer it in.
- `<skill-3>` — when to layer it in.
Invoke like:
`用 <skill-name> <Murphy's goal>`
```

Offer a ready prompt only when Murphy is choosing a workflow manually. If Murphy asked Codex to handle the task, proceed after naming the selected skill(s).

## First Observable Action

After routing, the user should know what happens next. Include one of these in the reason or immediately after it:

- ask one funnel question
- inspect repo/files
- verify path or environment
- browse official/current sources
- reproduce bug or gather logs
- draft the artifact
- edit the file and run checks
- create/update the automation
- continue learning mode with one prediction question

If there is no dedicated skill, say so briefly and execute directly.

## Murphy Learning Mode

Trigger when Murphy says "教我", "带我学", "我不懂", "第 0 步", "不要写代码", "面试我", "检查我理解", or asks for a learning session.

First action:

- Start from "第 0 步".
- Ask one prediction question or give one tiny task, then stop.
- Define any new English term before using it.
- Do not implement unless Murphy explicitly switches to implementation.
- If a terminal command is mechanical, run it and teach from the result.
- If notes are requested, preserve both Murphy's attempted explanation and the corrected version.

## Router Sync Protocol

Run this whenever Codex participates in installing, updating, modifying, configuring, accepting, deleting, disabling, or rejecting a skill source. Murphy does not need to say "帮我同步 router" after a successful install/update.

Read-only guard: if Murphy explicitly asks for only review, inspection, evaluation, or "不要改文件", do not edit the map. Instead, report whether sync would be needed and what would change.

1. Inspect the new/changed `SKILL.md` frontmatter and README if present.
2. Update `references/skill-map.md` with:
   - skill name, source/path, and one-line purpose
   - trigger phrases Murphy would naturally say
   - overlaps with similar skills and when to choose it instead
   - dependencies, caveats, stale paths, or restart requirements
   - plugin/connector/tool dependency if the route needs one
   - cost or external side-effect gate if relevant
3. If a skill was updated or its rules changed, update affected route cards and add/adjust eval cases when trigger phrases, overlaps, caveats, or first actions changed.
4. If Murphy says a skill should no longer be recommended but did not explicitly ask to delete files, add a disabled/hold note or demote the route; do not delete.
5. If Murphy explicitly asks to delete/remove a skill, verify exact name, absolute path, and delete scope before destructive action; after deletion, remove or mark the map entry and add a hold/deleted note when it prevents future confusion.
6. If the source is not installed because it is not a real Codex skill, add a short "Rejected or hold" note only if it prevents future confusion.
7. In the final answer, mention whether the router map was updated and whether a restart/inventory refresh may be needed.

Use `bash scripts/list-installed-skills.sh` to refresh the raw inventory when needed.

Before finishing a sync, check:

- inventory refreshed or intentionally skipped
- map entry added/updated/held
- overlaps and caveats recorded
- plugin/tool availability and paid/external gates recorded when relevant
- final answer mentions whether the router map changed

## Routing Feedback Protocol

Run this whenever Murphy corrects the route, a chosen skill fails for avoidable reasons, or a new natural phrase appears:

1. Identify the missed cue, wrong candidate, missing caveat, or unnecessary question.
2. Classify the failure as one of: `facet_miss`, `retrieval_miss`, `evidence_miss`, `rerank_miss`, `threshold_miss`, `dependency_miss`, `mode_miss`, `map_stale`, `tool_name_stale`, `safety_gate_miss`, `plugin_callability_miss`, `cost_gate_miss`, or `external_side_effect_miss`.
3. Add or update an eval case in `references/router-eval-cases.md`.
4. Update `references/skill-map.md` only if the failure came from a missing trigger, overlap rule, caveat, stale tool name, or recurring workflow.
5. Re-run the affected eval cases mentally or with subagent review before finalizing.

If the turn is read-only, do not update eval or map files; report the exact eval/map changes that should be made.

## Self-Evolution Protocol

Use this when Murphy asks for router self-evolution, long-term evolution, auto-improvement, baseline preservation, candidate promotion, rollback, or when repeated route feedback suggests the map should learn.

The current live router is protected by `baselines/baseline-2026-06-17/`. Do not edit or replace that baseline. Candidate changes must be staged under `candidates/<timestamp>-<slug>/` first and must pass the promotion gate before they become live.

Runtime files:

- `references/evolution-log.jsonl`: desensitized route experience only. Store prompt summaries, facets, candidates, chosen route, final route, correction summary, failure type, and success signal. Do not store full private prompts, secrets, large file contents, or raw personal data.
- `references/evolution-decisions.jsonl`: gate, promotion, rejection, and rollback decisions.
- `references/evolution-reports/`: human-readable first-run, failure, patch, second-run, and promotion reports.
- `current-release.json`: current live release and rollback pointer.

Workflow:

1. For route failures, append a desensitized log row unless Murphy asked for read-only analysis.
2. Run `python3 scripts/mine_router_failures.py --since 7d` to summarize repeated failures.
3. Run `python3 scripts/synthesize_router_cases.py --input references/evolution-log.jsonl` to create pending eval cases.
4. Run `python3 scripts/propose_router_patch.py` to create a bounded candidate. Candidate edits may only change route triggers, anti-cues, ambiguity rules, first actions, and eval cases.
5. Run `python3 scripts/evolution_gate.py --candidate candidates/<id> --suite all`. The gate must preserve baseline `hit@3=100%`, heldout/safety/regression suites, guard scripts, safety gate phrases, router-as-meta-pass behavior, visible routing notes, first observable actions, and diff budgets.
6. If the gate passes, generate a promotion recommendation packet only. Never auto-promote. A later, separate turn with Murphy's explicit approval may run `python3 scripts/promote_router_candidate.py --candidate candidates/<id> --approved-by-user`.
7. If promotion causes bad behavior, run `python3 scripts/promote_router_candidate.py --rollback`.

Never auto-promote a candidate that edits guard scripts such as `evolution_gate.py`, `promote_router_candidate.py`, `eval_router_dataset.py`, or `router_evolution_lib.py`. Guard-script changes require explicit human review outside the auto-evolution lane.

## Router v2 Decision Protocol

Router v2 is a recommendation layer, not an authority layer. Runtime output must use `decision_scope: recommendation_only` and `execution_authorized: false`. A correct route never grants permission to execute it.

Return these bounded, user-explainable fields without chain-of-thought or long internal reasoning:

```json
{
  "decision_id": "non-content decision fingerprint",
  "intent_family": "abstract task family",
  "candidate_skills": [{"skill": "route", "score": 0.0, "availability_status": "available"}],
  "selected_skill": "one primary route",
  "confidence": 0.0,
  "requires_confirmation": false,
  "risk_class": "read_only",
  "availability_status": "available",
  "fallback": "",
  "short_reason": "brief evidence-based explanation",
  "reflection_advisory": {
    "context_key": "abstract-context-only",
    "suggested_skill": null,
    "evidence_count": 0,
    "applied": false,
    "reason_code": "no_preference"
  }
}
```

Allowed risk classes are `read_only`, `workspace_write`, `external_action`, `sensitive`, and `financial`. Allowed availability states are `available`, `missing_dependency`, `plugin_required`, and `blocked`.

`external_action`, `sensitive`, `financial`, plugin installation, account/browser operations, and connector writes require confirmation by default. Model capability, route confidence, or passing evals never remove that requirement.

Block recursive self-modification: when a task asks the Router to modify or promote its own live release, select `Manual router review route`, return `availability_status: blocked`, and generate a candidate packet for human review. Router explanation and read-only route recommendation may still select `murphy-skill-router` itself.

Run a one-off decision with:

`python3 scripts/router_v2.py --query '<desensitized task summary>'`

## Router v3 Post-Task Correction

Router v3 adds a temporary preference overlay after the v2 base decision. It does not rewrite `skill-map.md`, `router-v2-rules.json`, the capability catalog, or any release pointer.

After a task, accept only the fields in `references/route-feedback.schema.json`. Reject unknown fields and never record a raw prompt, query, free-form note, chain-of-thought, diary/chat/mail/document body, cookie, credential, secret, or personal identifier. `post_task_reflection.py` appends sanitized outcome identifiers to `route-feedback.jsonl`; `build_preference_overlay.py` aggregates them into `router-preference-overlay.json`.

Only a verified `route_miss` may activate a preference. One explicit Murphy correction plus verified replacement success is sufficient for the exact abstract context. Agent or test inference needs three unique verified successes across at least two tasks. Model advice is always shadow-only. Dependency failures, execution failures, changed intent, ambiguity, duplicates, conflicts, expired evidence, or fingerprint drift may not activate a preference.

An active preference may only rerank an already-present, currently available Top-3 candidate. It cannot affect Router self-modification, plugins, system configuration, accounts/browsers, or any `external_action`, `sensitive`, or `financial` route. Risk may only stay equal or increase, confirmation may only stay equal or become required, and `execution_authorized` remains false. Conflicts are quarantined. TTL is 30 days. No feedback path may auto-promote.

The decision includes a bounded `reflection_advisory` with `context_key`, base and suggested skill, evidence count, applied flag, and reason code. This is a short audit record, not internal reasoning.

## Capability Catalog And Availability

`references/capability-catalog.json` is generated from installed `SKILL.md` frontmatter plus bounded manual overrides in `references/capability-overrides.json`. The generated catalog may contain names, descriptions, logical source paths, fingerprints, aliases, dependency names, risk defaults, and fallbacks. It must not contain secret values, raw prompts, mail bodies, diary text, cookies, credentials, or machine-specific home paths.

Refresh the candidate catalog with:

`python3 scripts/build_capability_catalog.py`

Keep `references/skill-map.md` and manual aliases. Catalog generation augments explicit mapping; it does not replace or silently rerank previously correct map entries.

Availability is checked at decision time. Installed local skill metadata means the route can be recommended, not that its runtime dependencies are usable. Missing environment variables return `missing_dependency`; uninstalled optional plugins return `plugin_required`; unavailable connectors or protected permissions return `blocked`. Every non-available result needs a concrete fallback and may not claim execution readiness.

## Shadow Routing

Shadow routing compares v1 and the v2 base plus v3 advisory without changing the default route or a release pointer. Inputs must be existing eval cases or pre-desensitized titles, intent labels, and task summaries. Never persist the raw private prompt.

Persist only case id, abstract intent, candidates, selected route, confidence, risk, confirmation, availability, fallback presence, and human/test feedback. Confusion reports cover v1/v2 disagreements, Top-1 errors, Top-3 misses, risk mistakes, unavailable-route mistakes, and candidate intents for new or merged capabilities.

Run:

`python3 scripts/shadow_route.py --suite all --output references/evolution-reports/router-v3-shadow-results.json --report references/evolution-reports/router-v3-confusion-report.md`

Shadow output remains advisory and cannot write a formal release.

## Model Review Advisory

Runtime routing uses deterministic map/catalog retrieval and rules. If confidence is below `0.70` or the candidate margin is below `0.08`, Router v2 may return `model_review.review_recommended: true`. It does not call a model automatically.

Offline model help may classify synthetic cases or suggest conflicts, but record only whether a model participated, a version label, and an estimated cost. Do not store the complete prompt, response, chain-of-thought, or key. Model review cannot authorize high-risk execution.

## Router v2 Promotion Gate

The release strategy is `manual_approval_after_gate`. Candidate changes must pass quick validation, focused tests, train, heldout, safety, regression, ambiguity, feedback, frozen-eval checks, immutable-baseline checks, and the v3 candidate gate.

Minimum thresholds are documented in `references/router-v2-rules.json`: train/heldout/ambiguity Top-1 at least 90%, safety Top-1 at least 95%, feedback behavior 100%, regression Top-1 at least the measured v1 baseline with zero new regressions, Hit@3 100%, risk under-classification and exact risk misclassification 0, confirmation false negatives 0, unavailable-route misleading rate 0, unsafe preference overrides 0, risk/confirmation downgrades 0, p95 latency at most 100 ms, runtime model calls 0, and runtime model cost 0.

Heldout is not used for tuning. A heldout or safety failure rejects that candidate. A later candidate may learn from safety/regression failure mining while keeping heldout wording out of rule development.

Passing the gate creates a recommendation packet only. It does not mean Router v2 safely executed tasks, and it does not authorize plugin installation, system changes, account access, financial actions, promotion, commit, or push. Guard-script changes always require explicit human review. Never auto-promote.

## Routing Discipline

- Prefer the narrowest skill that matches the immediate failure mode.
- Prefer 1-3 skills, not a giant chain.
- Recommend exactly 1 primary skill and at most 2 secondary skills.
- If the goal spans multiple categories, choose the most upstream useful skill first: clarify/spec before build, reproduce before fix, source-check before framework code, file-format skill before visual polish.
- Do not dump the full skill list. Use `references/skill-map.md` silently and surface only relevant choices.
- When skills overlap, choose by output surface first, then workflow risk, then tool dependency.
- Name the first observable action after choosing the route.
- If a skill has stale or personal paths, verify local paths before using it. Do not use `obsidian-vault` without confirming Murphy's real vault path.
- If the chosen route depends on an API key, CLI, connector, browser tool, live app, or stale personal path, name and verify the dependency when cheap before relying on it.
- For current facts, products, prices, docs, libraries, law, finance, or recommendations, browse or use official docs instead of memory.
- In learning mode, do not jump into implementation unless Murphy explicitly switches modes. Ask one prediction question or give one tiny task.
- If a request mentions RAG, routing, retrieval, evidence, rerank, or eval, separate the stages: query rewrite/search target, retrieval, rerank, evidence check, and final generation. Do not blur them.

## Recommendation Vs Execution

- If Murphy asks "what should I use?", recommend and offer a ready prompt.
- If Murphy asks "do this" or "帮我处理", route and execute.
- If Murphy asks "install/update/delete/check this skill", use the skill-install route: inspect the repo shape first, use an available installer skill/script only if present, then sync the map.
- If confidence is high, do not interview. State the selected skill(s) and move.
- If confidence is low, apply the Question Gate before asking one funnel question.

## Self-Check Before Final Answer

Silently verify:

- Did I show the user-visible routing note for non-trivial routed turns?
- Did I choose one primary route?
- Did I use at most two secondary routes?
- Did I explain why the primary skill/direct route was selected?
- Did I explain why visible candidate skills/routes were not selected when no dedicated skill is used?
- Did I distinguish recommendation vs execution?
- Did I treat a named skill correctly as workflow vs artifact?
- Did I avoid unnecessary questions?
- Did I open the primary skill's `SKILL.md` before applying it?
- Did I respect read-only / no-edit instructions?
- Did I state the first observable action?
- Did I keep enough route trace to explain top candidate, runner-up, margin, and threshold reason if challenged?
- Did I preflight dependency-heavy or stale-path routes?
- Did I preflight plugin/connector/tool availability before claiming use?
- Did I get approval for paid quota or external side effects when required?
- Did I protect learning mode when Murphy asked to learn?
- Did I verify current facts with official/current sources when required?
- Did I mention sync status if skills changed?

## High-Signal Defaults

- Unknown requirement: `quick-requirement-clarifier`; for larger new projects use `project-intake-interview`.
- Engineering feature: `spec-driven-development` -> `planning-and-task-breakdown` -> `incremental-implementation`; add `test-driven-development` when behavior changes.
- Hard bug: `diagnose` or `debugging-and-error-recovery`; use `superpowers:systematic-debugging` only when Murphy explicitly requests Superpowers or that workflow is already active.
- Frontend product surface: `frontend-design`; implementation details/components: `frontend-ui-engineering`; Figma source: `figma-implement-design`.
- Open Design canvas/design sidecar: `open-design-assistant`; use when Murphy says "打开 Open Design", "进入设计模式", "用 Open Design 画布", "读取/修改当前设计稿", or mentions `localhost:64392`.
- Polished deliverable/PDF/landing page: `kami`; editable `.pptx`: `pptx` or `pptx-skill`; professional `.docx`: `docx` or `doc`.
- Obsidian files: `obsidian-markdown`, `obsidian-bases`, or `json-canvas`; live vault operations require `obsidian-cli` and an installed Obsidian CLI.
- Wiki knowledge tasks: use `wiki-query`, `wiki-explain-page`, `wiki-ingest`, or `wiki-lint`, not Obsidian skills.
- Skill authoring or router upgrades: `superpowers:writing-skills` plus `write-a-skill` / `create-expert-skill` as needed.
- Plugin/connector work: use the matching plugin/app/tool route when callable; otherwise recommend or request installation only under the install rules.
