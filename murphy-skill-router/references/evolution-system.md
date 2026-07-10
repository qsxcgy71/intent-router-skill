# Router Self-Evolution System

This directory turns `murphy-skill-router` into a guarded long-term learning system. Router v2 is shadow-only and never promotes automatically. It may produce a promotion recommendation only after baseline comparison, suite validation, safety checks, release snapshots, and rollback verification.

## Data Files

- `evolution-log.jsonl`: desensitized route experience. Do not store full private prompts, secrets, raw personal data, or long file contents.
- `evolution-decisions.jsonl`: gate, promotion, rejection, and rollback records.
- `evolution-reports/`: human-readable reports from gate and promotion runs.
- `pending-router-eval-cases.json`: generated cases waiting to be reviewed or merged into a candidate.

Required log fields:

```json
{
  "timestamp": "2026-06-17T12:00:00Z",
  "prompt_summary": "desensitized user intent summary",
  "facets": ["router", "self-evolution"],
  "candidates": ["murphy-skill-router", "Murphy router self-evolution route"],
  "chosen_primary": "murphy-skill-router",
  "final_route": "Murphy router self-evolution route",
  "user_correction_summary": "why the route needed correction",
  "failure_type": "rerank_miss",
  "success_signal": false
}
```

## Candidate Lifecycle

1. Mine failures: `python3 scripts/mine_router_failures.py --since 7d`
2. Synthesize cases: `python3 scripts/synthesize_router_cases.py --input references/evolution-log.jsonl`
3. Propose candidate: `python3 scripts/propose_router_patch.py --case-file references/pending-router-eval-cases.json`
4. Refresh the candidate catalog: `python3 scripts/build_capability_catalog.py`
5. Run v2 shadow evaluation: `python3 scripts/shadow_route.py --suite all --output references/evolution-reports/router-v2-shadow-results.json --report references/evolution-reports/router-v2-confusion-report.md`
6. Gate candidate: `python3 scripts/evolution_gate.py --candidate candidates/<id> --suite all`
7. Generate a promotion recommendation packet; do not promote in the same run.
8. Only after a separate explicit user approval: `python3 scripts/promote_router_candidate.py --candidate candidates/<id> --approved-by-user`
9. Roll back if needed: `python3 scripts/promote_router_candidate.py --rollback`

## Hard Rules

- `baselines/baseline-2026-06-17/` is immutable.
- Automatic promotion is disabled. Guard-script changes always require human review.
- Baseline, heldout, safety, regression, and ambiguity suites must remain `hit@3=100%`.
- Heldout is frozen and not used for tuning.
- Risk misclassification, risk under-classification, confirmation false negatives, and unavailable-route misleading rate must remain zero.
- Runtime model calls and runtime model cost must remain zero; p95 route latency must stay at or below 100 ms.
- Safety phrases for cost, external side effects, plugin preflight, visible routing, and router-as-meta-pass must remain present.
- Bounded candidates may alter route triggers, anti-cues, ambiguity rules, first actions, and eval cases.
- Shadow logs store only case ids, abstract intents, structured decisions, and feedback. They never store raw private prompts.
