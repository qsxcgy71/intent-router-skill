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

The live candidate passed 42 focused/system tests, quick validation, and all six evaluation suites before packaging. To configure a local copy, first generate its own capability catalog:

```bash
python3 scripts/build_capability_catalog.py
```

Create a local `current-release.json` and empty `references/route-feedback.jsonl` before running the full live validation sequence. Both are deliberately excluded from this public package.
