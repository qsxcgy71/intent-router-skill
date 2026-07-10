# Router v3 Maintenance

## After adding or updating a skill

1. Inspect the installed `SKILL.md` frontmatter and verify the skill is in an active root.
2. Run `python3 scripts/build_capability_catalog.py`.
3. Review the generated catalog diff. It may contain metadata, logical source, fingerprint, aliases, dependency names, risk, availability policy, and fallback only.
4. Add manual aliases or dependency categories to `capability-overrides.json` when metadata cannot express a stable distinction.
5. Keep `skill-map.md` entries and ambiguity notes when they already provide correct explicit routing.
6. Add synthetic cases to train for rule development. Add truly unseen wording to heldout and freeze it before implementation. Put high-risk cases in safety, preserved old behavior in regression, and close-candidate cases in ambiguity. Never reuse an id across suites.
7. Do not copy private task text into any dataset. Use an abstract task category and a short synthetic paraphrase.
8. A skill/catalog fingerprint change automatically stales any matching feedback preference. Rebuild and review the overlay; never carry an old preference across unreviewed capability drift.

## After a route correction

1. Confirm the final skill actually succeeded and that the problem was a `route_miss`, not missing dependencies, execution failure, changed intent, or ambiguity.
2. Construct only the structured fields in `route-feedback.schema.json`; do not include the task text or free-form notes.
3. Run `python3 scripts/post_task_reflection.py --event <sanitized-event.json>`.
4. Run `python3 scripts/build_preference_overlay.py`.
5. Inspect active, shadow-only, and quarantined counts. Explicit verified user correction needs one event; inferred evidence needs three unique events across two tasks.
6. Run the feedback suite and all normal gates. The overlay remains candidate/shadow state and never modifies official rules.

## Candidate validation sequence

Run from a candidate workspace:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache python3 scripts/test_router_v2.py
PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache python3 -m pytest -q scripts/test_router_feedback.py
PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache python3 scripts/test_evolution_system.py
PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache python3 scripts/eval_router_v2.py --suite train --show-failures
PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache python3 scripts/eval_router_v2.py --suite heldout --show-failures
PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache python3 scripts/eval_router_v2.py --suite safety --show-failures
PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache python3 scripts/eval_router_v2.py --suite regression --show-failures
PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache python3 scripts/eval_router_v2.py --suite ambiguity --show-failures
PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache python3 scripts/eval_router_v2.py --suite feedback --show-failures
PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache python3 scripts/shadow_route.py --suite all --output references/evolution-reports/router-v3-shadow-results.json --report references/evolution-reports/router-v3-confusion-report.md
PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache python3 scripts/evolution_gate.py --candidate . --suite all --write-report
```

Also run the system skill `quick_validate.py` against the candidate skill directory. `parse_router_eval_cases.py` must continue to parse all case-list YAML blocks and ignore the schema block.

## Freeze and tuning discipline

- Tune deterministic rules on train.
- Freeze rule and suite hashes in `eval-freeze.json` before the final heldout gate.
- Do not tune from heldout wording.
- A failed candidate is recorded as rejected. A later candidate may use safety/regression failure mining while preserving heldout isolation.
- Keep ambiguous label conflicts in a manual-label report; do not force a rule merely to reach 100% Top-1.

## Promotion and rollback

Passing the gate means “eligible for human review,” not “promoted.” The default strategy is `manual_approval_after_gate`; `--auto` is rejected.

After a separate explicit approval, the promotion script first saves a complete pre-promotion live snapshot, writes the candidate release, and points rollback at that snapshot. The rollback command restores that snapshot. Do not edit the immutable `baseline-2026-06-17` directory.

## Availability maintenance

Use runtime availability snapshots for connectors and tools. Store booleans or capability names only, never session cookies, tokens, account data, or secret values. If callability cannot be verified, return `blocked` or `plugin_required` with a safe fallback.

`route-feedback.jsonl` is runtime evidence and is deliberately excluded from promoted release snapshots. The schema, empty/default overlay, evaluator, and policy are promotable; private task outcomes are not.
