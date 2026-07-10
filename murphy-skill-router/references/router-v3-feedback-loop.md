# Router v3 Post-Task Feedback Loop

Router v3 keeps the v2 deterministic catalog/rule/retrieval route as the base. Post-task evidence can suggest a better skill on a later matching abstract context, but it cannot change execution authority.

## Flow

`base route -> structured outcome -> validation -> evidence aggregation -> temporary overlay -> bounded Top-3 rerank -> safety recheck`

## States

- `active`: evidence threshold met, no conflict, unexpired, fingerprints current.
- `shadow_only`: insufficient evidence, inferred/model-only advice, or expired evidence.
- `quarantined`: conflicting verified replacement skills.
- ignored: malformed, duplicate, non-route failure, failed/unverified, or unavailable replacement.

## Safety invariants

- No raw task text or sensitive content is stored.
- No skill outside the base Top-3 is introduced.
- No unavailable target is selected.
- Protected intent/risk classes cannot be reranked.
- Risk and confirmation cannot be downgraded.
- Execution remains unauthorized.
- Official maps, rules, release pointers, and baselines are not written.
- Feedback never triggers promotion.

## Operational note

The runtime ledger is local candidate evidence and is excluded from release snapshots. A generated overlay stores only context/skill identifiers, counts, timestamps, state, and fingerprints. Emptying or disabling it restores the v2 routing fields.
