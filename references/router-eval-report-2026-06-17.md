# Router Eval Report - 2026-06-17

This note documents the test-driven update that added a top-k routing dataset and the upstream discovery rule.

## Why This Test Set Exists

The failure that motivated this update was not a missing domain route. The router could recall domain/action routes such as implementation, research, and automation. The problem was that it could choose those too early, before clarifying a broad, high-risk redesign request.

The dataset therefore tests whether the router can retrieve the correct *first workflow*, not just a related skill. Each case records:

- the user prompt
- the expected primary route
- useful support routes
- routes that must not win top-1
- the reason the case exists

The scoring script reports `hit@3`: the expected primary route must appear in the first three retrieved routes, and forbidden top-1 routes must not win.

## Dataset Construction

The cases were built by checking route-card trigger language against common user scenarios:

1. Upstream discovery vs direct action: broad redesign, emotionally negative feedback, adapting another project, scheduled/external action.
2. Requirements vs implementation: fuzzy existing repo changes, new projects, clear implementation tasks.
3. Debugging/review/building: production errors, test failures, code review, TDD.
4. Frontend/browser/document output: visual polish, UI behavior, browser operation, docx, pptx, PDF.
5. Plugins and external side effects: plugin recommendation, missing connector, paid API, deployment, automation.
6. Knowledge/data/git/skill maintenance: local knowledge bases, spreadsheets, GitHub publishing, skill updates.

The dataset is intentionally broad but plain: it is a regression guard for route recall, not a semantic benchmark.

## Example Cases

### 1. Broad Redesign With Scheduled Action

Prompt:

```text
Use intent-router. The current automation system is terrible; search again, build on another project, and redesign it into a personalized, verifiable, iterative system with scheduled actions.
```

Expected primary:

```text
upstream discovery / brainstorming route
```

Useful follow-ons:

```text
docs/official-source route, automation/reminder route, incremental implementation
```

Why:

The first action should clarify purpose, constraints, risk boundaries, and validation loop. It should not schedule actions or start implementation before the design direction is approved.

### 2. Fuzzy Existing Repo Change

Prompt:

```text
This existing repo needs a feature, but I cannot describe it clearly yet. Help me shape this change.
```

Expected primary:

```text
requirements clarifier
```

Why:

The repo already exists and the change is close to implementable, so one funnel question is better than a full new-project intake.

### 3. Editable PowerPoint

Prompt:

```text
Make an editable PowerPoint PPTX deck, not just a PDF.
```

Expected primary:

```text
presentation route
```

Why:

The output surface is explicit. Editable Office routes must beat polished-PDF routes.

### 4. Missing Connector

Prompt:

```text
Use the Slack connector to find the latest team decision.
```

Expected primary:

```text
missing plugin boundary
```

Why:

The router must check callability before claiming it used a connector.

## First Run

The first run used a deliberately simple lexical scorer over the existing route map plus installed skill descriptions.

Result:

```text
cases=40 top1=13/40 hit@3=22/40 (55.0%)
```

Problems exposed:

- The broad automation redesign case did not retrieve upstream discovery. It retrieved unrelated or downstream routes first.
- Prompts that explicitly named the router encouraged the router itself to win instead of selecting the downstream route that should do the work.
- Some domain/action routes, such as automation, implementation, or research, were attractive lexical matches but wrong first actions.
- The route map lacked explicit trigger language for broad redesign, "build on another project", "verifiable/iterative system", and scheduled high-risk action.
- Some comparison rows and ambiguity rows were noisy retrieval candidates, so the evaluation script had to ignore non-route tables.

## Changes Made

1. Added a router-as-meta-pass rule: when the user names the router while asking for a real task, the router stays visible as the routing pass but does not become the terminal primary route.
2. Added an Upstream Discovery Gate to `SKILL.md`.
3. Added an upstream discovery route card to `references/skill-map.md`.
4. Added ambiguity rules for broad unclear redesign and router-as-meta-route.
5. Added `references/router-eval-dataset.json` with broad top-k cases.
6. Added `scripts/eval_router_dataset.py` for a repeatable `hit@k` check.
7. Added a golden eval case to `references/router-eval-cases.md` for the router-named broad-redesign failure.

## Second Run

After normalizing route names, excluding non-route comparison tables from retrieval, and adding the upstream discovery triggers:

```text
cases=40 top1=37/40 hit@3=40/40 (100.0%)
failures: none
```

The public dataset in this repository is smaller and generalized, but it keeps the same structure and the same regression: broad high-risk redesign should route to upstream discovery before action.

Run it with:

```bash
python3 scripts/eval_router_dataset.py --show-failures
```
