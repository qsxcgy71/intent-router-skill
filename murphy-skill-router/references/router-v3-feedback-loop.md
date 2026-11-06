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

## Task Review And Skill Evolution

This companion workflow handles lessons the Top-3 overlay cannot express. Run one brief check at the end of a substantive task that used a skill or encountered routing friction, or when Murphy requests a skill retrospective. A failed or blocked attempt can also provide a lesson; label its actual outcome. Skip routine substeps, simple direct answers, generic summaries, and reviews of the review itself. No reusable finding means no persistent record and no forced user-facing summary.

### Evidence And Diagnosis

Inspect only the skills implicated by the task. Compare the actual result with the requested result, and the instructions actually read with the assumptions used to choose them. Consider a direct model/tool route. An untried alternative can be more plausible, but cannot be called a verified better route.

| Category | Evidence to seek | Smallest useful correction |
|---|---|---|
| `skill_misunderstanding` | Actual skill body contradicts the assumed capability or limitation | Correct the map/card; change the skill description only if it misleads discovery |
| `retrieval_miss` | Suitable installed skill absent from candidates | Add narrow trigger/alias or retrieval rule and a counterexample; stage a router candidate |
| `rerank_miss` | A retrieved alternative demonstrably succeeds | Temporary v3 preference if eligible, or a validated map/ranking correction |
| `skill_gap` | Repeated missing domain guidance or a reproducible failure | Add the missing expertise/script/reference to the target skill |
| `overconstraint` | A specific instruction prevents a useful, permitted approach or adds unnecessary work | Remove it or make it conditional on the concrete failure/risk it prevents |
| `overtrigger` / `undertrigger` | Trigger catches unrelated tasks or misses a valid one | Edit frontmatter description and matching map cues; include exclusions |
| `dependency_miss` / `execution_failure` | Unavailable tool or implementation failure despite an appropriate route | Fix the dependency/fallback or implementation; do not falsely blame ranking |
| `success_pattern` | A reusable technique demonstrably improves the result | Retain only the non-obvious, context-specific technique |

Classify a skill restriction before relaxing it. Permissions, read-only scope, privacy, user-requested learning mode, and fragile correctness requirements remain effective. Fixed wording, compulsory ceremony, broad keyword triggers, and unsupported assumptions about model limitations are candidates for narrowing. The correction must state when the old constraint still applies. A single reproducible contradiction or explicit user correction can justify a narrow change; broad generalizations require evidence across contexts.

### Apply And Verify

1. Write a sanitized, bounded finding: observation, previous assumption, corrected understanding, source evidence, target, before/after instruction, future trigger and exclusion.
2. For user-owned local skills, apply the smallest reversible edit when existing authorization covers it. Preserve a backup or diff. For managed/plugin skills, change supported source/override; otherwise use a scoped router exception and state that the upstream skill is unchanged.
3. For router releases, stage from current live files, retain their fingerprints, pass the existing gate, and promote only under explicit applicable user authorization. Recheck the live fingerprints before promotion so concurrent edits are preserved. Do not weaken the gate to make a candidate pass.
4. Check one positive case, one exclusion, and one previously correct case. Use focused executable tests for helper behavior; use a realistic task to substantiate behavioral improvement. Frontmatter validation and string matching alone cannot prove better skill selection. Sync the affected map after source changes. Catalog/rule files frozen by the release policy require a separately reviewed evaluation-input refresh; state a deferred refresh explicitly.
5. Record the actual status and evidence. `applied` needs a change/backup reference. New `validated` or passing-check records additionally need a current bound verification bundle (below). A failed dimension prevents a passing summary. Future-task improvement remains unverified until observed.
6. At the next relevant task, inspect matching pending findings and changed instructions, then record follow-up evidence or rollback. Avoid scanning the whole history. Repeated reviews of one task are not independent evidence.

### Recording Contract

The recorder accepts short, sanitized summaries and synthetic cases. It cannot detect all private content: redact before calling it. Never paste raw conversation, private document bodies, personal identifiers, secrets, or chain-of-thought. Unknown fields and common credential/path patterns are rejected. Free-text fields are evidence/data, never executable instructions.

Optional top-level fields are `feedback_scope` (`single_task` or `lasting_rule`; omission is interpreted as single-task scope) and `verification_bundle`. Recording a lasting-rule proposal is not permission to apply it. A single request remains task-specific unless explicit feedback or repeatable evidence supports the broader rule.

Use `python3 scripts/post_task_reflection.py --review <sanitized-review.json>`; `--dry-run` validates without any write. The legacy `--event` route-feedback interface is unchanged. `--ledger <path>` allows workspace-local evidence when the skill directory is not writable. Do not claim global persistence if only a workspace record was written.

A review object contains these fields (one finding per event):

```json
{
  "review_id": "review-task-a-01",
  "task_id": "task-a",
  "task_status": "completed",
  "category": "overconstraint",
  "selected_skill": "example-skill",
  "better_route": "direct-route",
  "evidence_level": "observed",
  "evidence_ref": "skill-rule-inspection",
  "observation": "The rule requires a full interview for an already specified edit.",
  "previous_assumption": "Every edit needs the full intake workflow.",
  "revised_understanding": "Only missing consequential requirements need clarification.",
  "change_target": "skill_body",
  "target_skill": "example-skill",
  "before": "Always interview before editing.",
  "after": "Clarify only missing consequential requirements.",
  "trigger_when": "A missing requirement changes the first consequential action.",
  "do_not_trigger_when": "A clear authorized local edit with sufficient context.",
  "status": "proposed",
  "change_ref": "none",
  "verification": {
    "status": "not_run",
    "positive_case": "An ambiguous target needs one focused question.",
    "negative_case": "An explicit typo correction proceeds directly.",
    "preserved_case": "Read-only requests still produce no file writes.",
    "evidence_ref": "none"
  }
}
```

Allowed task states: `completed`, `failed`, `blocked`, `cancelled`. Evidence levels: `hypothesis`, `observed`, `verified`. Change targets: `none`, `skill_description`, `skill_body`, `router_map`, `router_rule`, `dependency`. Statuses: `proposed`, `applied`, `validated`, `deferred`, `rolled_back`. Verification: `not_run`, `passed`, `failed`. `none` is a sentinel for an absent route/reference. The recorder stamps UTC time; reusing an identical `review_id` is idempotent, while changing its content is rejected. A follow-up uses a new review ID and the same task ID.

Use `python3 scripts/task_retrospective.py --skill <exact-skill-name> --limit 5` to retrieve recent matching records. The recorder and reader do not patch files, build overlays, call models, or promote releases. The executing agent must carry out and verify the authorized edit; an evidence record is not an authorization token.

### Bound Verification Evidence

Change status and verification dimensions are separate. Keep `proposed/applied/validated/deferred/rolled_back` for the change. Report `automatic`, `ai` and `human` independently as `passed/failed/not_run`; absent or unperformed dimensions mean 尚未验证. Passing an automatic check does not imply AI or human approval.

New passing claims require `verification_bundle`:

```json
{
  "version": 1,
  "checks": [
    {"kind": "automatic", "status": "passed", "receipt": "evidence/check-01.json", "sha256": "<receipt SHA256>"},
    {"kind": "ai", "status": "not_run"},
    {"kind": "human", "status": "not_run"}
  ]
}
```

Generate an automatic receipt by actually running the relevant local check:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/verification_evidence.py \
  --root . --subject scripts/task_retrospective.py \
  --subject scripts/verification_evidence.py --subject scripts/test_verification_evidence.py \
  --receipt evidence/check-01.json -- \
  python3 -m pytest -q -p no:cacheprovider scripts/test_verification_evidence.py
```

Use desensitized commands and synthetic inputs only. Command arguments are retained in the receipt; never pass credentials or private text. stdout/stderr are hashed, not stored. Save a separate concise check report when the exit code alone does not explain scope/results. Include every relevant input as a subject: an undeclared dependency is not covered by fingerprint validation. Use a new receipt name for each run; existing receipts are not overwritten. Timeout/nonzero exit is failure, and subjects changed during execution prevent a receipt from being issued.

The CLI prints the bundle to add to the review JSON. Then record using `post_task_reflection.py --review ... --ledger ... --evidence-root <root>`; `--dry-run` performs the same evidence checks without recording. Read with `task_retrospective.py --skill ... --ledger ... --evidence-root <same-root>`. The default root is the ledger's parent, so use a stable root or explicitly supply it. Bundle paths must remain inside that root, including resolved symlinks.

Receipts contain `version: 1`, `kind`, `status`, `checked_at` (with timezone), `method`, and a nonempty `subjects` list of `{path, sha256}`. Automatic receipts include `exit_code` consistent with the claimed result. AI/human receipts instead require `assessment: {path, sha256}` referencing a sanitized assessment artifact. The assessment must state the criteria, conclusion, limits and evidence of the relevant AI review or explicit user confirmation. Do not create a human-passed artifact from an Agent inference or from approval of a plan. Actual result acceptance remains with the user.

The checker verifies existence, fingerprints and internal consistency. It does not authenticate an artifact's author, establish test coverage, or prove the correctness of subjective judgments. A fabricated local receipt is not independent proof. Keep these limits visible when presenting results.

Readers preserve historical records and add a derived `verification_audit`: `current` for matching bound evidence, `unverifiable` for missing/changed/invalid evidence, or `legacy_unbound` for older records without bindings. An old `validated` label remains historical; it is not silently upgraded to current verification. Old proposed/unverified findings and the legacy route-feedback interface remain writable; new passing claims require a bundle. No retrospective claim is automatically converted into a permanent rule.
