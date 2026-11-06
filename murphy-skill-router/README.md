# Murphy Skill Router v3

This directory contains a sanitized, reviewable public source package derived from Murphy's live Router v3 release. It is not a copy of private runtime state.

## Included

- deterministic catalog/rule/retrieval routing
- structured recommendation-only decision protocol
- capability catalog generation, a minimal public example, and availability fallbacks
- isolated train, heldout, safety, regression, ambiguity, and feedback suites
- privacy-preserving shadow comparison
- bounded post-task feedback and temporary Top-3 preference overlay
- candidate gate, promotion, and rollback tooling
- task-level review records with explicit single-task/lasting-rule scope
- command receipts and subject fingerprints, with independent automatic/AI/human states

## 2026-11 maintenance upgrade

Start with the work map in `SKILL.md`. Routine route-map sync does not refresh frozen catalog/rule inputs. New passing review claims require bound receipts; historical records remain readable and are marked `legacy_unbound` when no binding exists. See [the feedback contract](references/router-v3-feedback-loop.md) and [the before/after experiments](../experiments/verification-upgrade/README.zh-CN.md).

## Deliberately excluded

- machine-local release ids, candidate paths, rollback snapshots, baseline manifests, and eval checksums
- the complete generated inventory of locally installed capabilities
- route feedback, evolution decisions, and evolution logs
- reports containing local candidate paths
- releases, candidates, rollback snapshots, caches, and backups
- tokens, cookies, prompts, diary/mail/chat/document contents, and other private runtime data

The committed `router-preference-overlay.json` is an empty static default. `capability-catalog.example.json` contains illustrative public metadata only. Runtime evidence and a real generated inventory must remain local and must never be committed.

## Safety

Routing is recommendation-only. A matching skill does not authorize execution. External actions, sensitive/account/browser work, financial actions, plugin installation, and system configuration remain confirmation-gated or blocked. Feedback cannot introduce a skill outside the current available Top-3, reduce risk, remove confirmation, edit official rules, or auto-promote itself.

## Validation

The November live candidate passed 88 distinct focused/system tests, structural validation, and the existing promotion gate. The paired local routing results remained unchanged (123/124 Top-1, 124/124 Hit@3). The public source package has a self-contained subset of 46 review/evidence tests, which passed without the private catalog:

```bash
# Run from the repository root; pytest is needed only for these tests.
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  murphy-skill-router/scripts/test_task_retrospective.py \
  murphy-skill-router/scripts/test_verification_evidence.py
python3 experiments/verification-upgrade/run_experiments.py --output /tmp/router-comparison.json
```

The experiment uses only the Python standard library. `skill-system-upgrader/` is a separately installable skill; copy it into your agent's skills directory when using that workflow.

For a fresh, unfrozen local setup, generate your own capability catalog from this subdirectory:

```bash
python3 scripts/build_capability_catalog.py
```

Full live release validation additionally requires your own overrides, release state, immutable baseline, evaluation freeze record and empty runtime ledger. These are deliberately excluded from the public package. A fresh clone cannot reproduce the author's private frozen-config gate by creating placeholder files. For an already frozen deployment, follow the separate evaluation-input maintenance procedure before refreshing its catalog.
