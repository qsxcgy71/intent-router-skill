# Router v2 Architecture and Decision Protocol

## Objective

Router v2 improves recommendation accuracy, explainability, risk labeling, and dependency fallbacks while keeping execution authority unchanged. It is an additive layer over the existing map and v1 evaluator, and it remains shadow-only until separately approved.

## Data flow

1. `build_capability_catalog.py` scans active local, Superpowers, and installed plugin skill roots.
2. It reads `SKILL.md` frontmatter, normalizes source paths, fingerprints source files, and merges `capability-overrides.json`.
3. `router_v2.py` retrieves from the existing map, consults catalog aliases, applies deterministic intent/risk rules, checks availability, and emits a structured recommendation.
4. `shadow_route.py` compares v1 and v2 using eval cases or already-desensitized summaries.
5. `eval_router_v2.py` measures routing, risk, confirmation, availability, latency, and model cost.
6. `evolution_gate.py` validates frozen data, immutable baseline files, suite isolation, thresholds, and release strategy.
7. Passing creates a promotion recommendation only. `promote_router_candidate.py` rejects `--auto` and requires a later `--approved-by-user` invocation.

## Decision contract

Every response contains:

| Field | Meaning |
|---|---|
| `intent_family` | Abstract task family, not the raw prompt |
| `candidate_skills` | Up to three scored routes plus availability |
| `selected_skill` | One primary recommendation |
| `confidence` | Bounded 0-1 confidence in route fit |
| `requires_confirmation` | Whether execution needs explicit confirmation |
| `risk_class` | `read_only`, `workspace_write`, `external_action`, `sensitive`, or `financial` |
| `availability_status` | `available`, `missing_dependency`, `plugin_required`, or `blocked` |
| `fallback` | Safe next route when execution is unavailable |
| `short_reason` | Short evidence-based explanation without chain-of-thought |

The engine also sets `decision_scope: recommendation_only`, `execution_authorized: false`, and a model-review record. High-risk classification forces confirmation even when route confidence is high.

## Retrieval and rule boundaries

- The existing `skill-map.md` remains the stable retrieval surface.
- The catalog augments missing routes and supplies aliases, risk defaults, dependencies, availability, and fallbacks.
- Catalog evidence cannot silently rerank an already correct explicit map entry.
- Exact, auditable rules handle high-risk boundaries and recurring intent families.
- A low-confidence or close-margin result may set `model_review.review_recommended`, but the runtime does not call a model.

## Availability semantics

An installed skill file means its instructions are discoverable. It does not prove that a connector, CLI, environment variable, account, browser session, or protected permission is usable. Availability is resolved at decision time without reading secret values:

- missing environment name -> `missing_dependency`
- optional uninstalled plugin -> `plugin_required`
- missing connector or protected action -> `blocked`
- available local/direct route -> `available`

Every non-available primary route must contain a fallback and remains unauthorized for execution.

## Privacy and model policy

Catalogs and shadow outputs never persist raw prompts, diaries, email bodies, chats, cookies, keys, document contents, or long reasoning traces. Source paths are logical and home paths are normalized. Offline model assistance may be used later for synthetic case grouping or conflict suggestions, but only model-used, version label, and estimated cost may be recorded.

## Recursion boundary

Router explanation may select `murphy-skill-router`. A request for the Router to change or promote its live self is instead routed to `Manual router review route`, marked `blocked`, and converted into a candidate review packet.
