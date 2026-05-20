# Intent Router Skill Map

Last synced: 2026-05-20.

This file is the router's working map. Keep it concise and decision-oriented. It does not replace each selected skill's `SKILL.md`; it only explains which route to open or use first.

## Attribution

This project uses the `skill-router` agent skill listed on EliteAI.tools as a reference:

- https://eliteai.tools/agent-skills/skill-router
- Listed source: `sickn33/antigravity-awesome-skills/skills/skill-router`

Useful borrowed pattern:

- short interview when the user is lost
- one primary skill plus at most two secondary skills
- exact invocation text the user can copy
- no full library dump
- pick the upstream skill first when a goal spans categories

This map extends that pattern with route evidence, reranking, visible route notes, plugin/tool preflight, safety gates, and maintenance rules.

## RAG Mental Model For Routing

Think of the user request as the query and this file as the retrieval corpus.

| RAG Stage | Router Equivalent | Failure To Avoid |
|---|---|---|
| Query understanding | Classify intent, output surface, risk, dependency, and recommendation vs execution | Treating every request as generic "which skill?" |
| Retrieval | Pull 2-5 candidate routes from this map | Only matching obvious words and missing intent |
| Evidence | Match trigger phrase, output format, dependency, caveat, and anti-cue | Picking a skill with no concrete evidence |
| Rerank | Choose 1 primary and at most 2 secondary routes | Dumping a chain of skills |
| Threshold | Ask one funnel question when wrong routing would waste time, money, files, or learning mode | Asking questions when the route is already clear |
| Generation | Say route, reason, and first observable action, then recommend or execute | Giving a label without next move |
| Eval | Compare against golden cases after changes | Assuming the map is good because it feels plausible |

Default visible route note:

```text
Routing note: detected <cue>; candidates were <A>, <B>, <direct route>; selected <primary> because <evidence>; did not use <candidate> because <anti-cue>; next step: <first action>.
```

## Global Maintenance Rule

This map is intended to be customized by each user. It is not limited to a single project, but it is also not a background watcher.

After every skill install, update, rule/config change, delete, disable, or "is this a skill?" inspection:

1. Add or update the skill entry without requiring a second "sync router" request.
2. Add overlap notes if it resembles an existing route.
3. Record dependencies and caveats, especially missing CLIs, stale paths, connector requirements, or restart requirements.
4. Record paid quota, deployment, publishing, messaging, or external-write gates when relevant.
5. If the user says a skill should not be recommended but does not explicitly request deletion, demote or hold the route. Do not delete files.
6. If the user explicitly requests deletion/removal, verify exact skill name, absolute path, and delete scope before destructive action.
7. If the source is not installed because it is not a real skill, add a hold note only if it prevents future confusion.
8. Compare affected behavior against `references/router-eval-cases.md`.

## Plugin, Connector, Cost, And Side-Effect Rules

| Situation | Route | Rule |
|---|---|---|
| Plugin/tool appears relevant | Plugin/connector preflight | Check whether a callable tool exists in this session; use tool discovery when available before falling back. |
| Tool is callable | Execute via plugin/app/tool route | Still show visible routing note and dependency caveats. |
| Tool is not callable | Recommendation or install-boundary route | Do not pretend it was used. Recommend it or request install only when the user explicitly asks for that exact known installable plugin/connector. |
| User asks "which plugin?" | Guided recommendation mode | Recommend only. Do not install or execute. |
| Metered API, image/audio/video generation, paid model call | Cost gate first | Having a key is not spending approval. State scope/quota/cost risk and ask before first paid call. |
| Deploy, send email, write cloud docs, write calendar, create automation, publish/share | External side-effect gate first | Confirm target/account/env/public-vs-private details when unclear or risky. |
| Read-only review | No write/call/install route | Report what would be done. Do not mutate router, external state, or files. |

## Route Card Template

Use this for high-frequency routes and overlaps:

```yaml
route:
type: local skill | plugin skill | connector/tool | direct
user_might_say:
first_action:
choose_instead_of:
ask_before:
dependencies:
caveats:
eval_ids:
```

## Starter Route Cards

These examples are intentionally generic. Replace names and caveats with the skills and plugins installed in your own environment.

| Route | User Might Say | First Action | Choose Instead Of | Ask Before | Caveats |
|---|---|---|---|---|---|
| requirements clarifier | "I know the repo but the feature is fuzzy", "help me shape this change" | Ask one funnel question or inspect nearby files | project intake for brand-new products | Wrong first action would edit files | Do not over-interview. |
| project intake | "I want to build a new app/tool/site from scratch" | Ask the first product/context question | requirements clarifier for existing scoped changes | Audience, output, platform unclear | Good for new projects. |
| systematic debugging | "do not guess", "production 500", "intermittent bug" | Reproduce or inspect logs before fixing | generic implementation | Target service/log path unknown | Use for hard or unclear bugs. |
| error recovery | "tests fail", "build failed", "this command errors" | Read exact error and run smallest repro | systematic debugging for intermittent bugs | Repro command or write scope unknown | Broad recovery route. |
| test-driven implementation | "red-green-refactor", "serious behavior change" | Write failing behavior test first | generic implementation | No behavior surface known | Use when tests can define the change. |
| incremental implementation | "build this feature", "make the change" | Inspect repo, plan thin slices, edit and verify | project intake when spec is vague | Target files or acceptance criteria unclear | Pair with tests for behavior changes. |
| code review | "review this diff", "any bugs?", "read-only review" | Inspect diff and list findings first | implementation route | Diff/branch unclear | Findings before summary. |
| frontend design | "looks cheap", "make it feel polished", "landing page" | Inspect current UI and visual target | UI engineering for state/accessibility bugs | App URL/path unclear | Verify visually after changes. |
| UI engineering | "responsive/state/accessibility issue", "component behavior" | Inspect components and UI state | frontend design for visual taste | Visual vs behavioral issue unclear | Pair with browser verification. |
| browser tool route | "open localhost", "click this", "screenshot the page" | Use the in-app browser or browser automation tool | scripted tests when repeatability matters | URL/port missing | Prefer interactive browser for explicit click/open requests. |
| scripted browser tests | "write an e2e test", "repeat this browser flow" | Inspect test setup and script flow | interactive browser route | App start command unclear | Use when repeatability matters. |
| docs/official-source route | "latest docs", "current pricing/model/API" | Browse official/current sources | memory-only answer | Product/context ambiguous | Separate official facts from inference. |
| Word document route | "make a docx", "Word file", "report I can submit" | Draft/edit/export `.docx` | polished PDF route | Identity/rubric/source missing | Use document tooling, not only chat summary. |
| presentation route | "make slides", "PPT/PPTX", "editable deck" | Create/edit `.pptx` and verify render | polished PDF route | Audience/slide count/storyline missing | Editable deck beats PDF polish. |
| PDF/polished deliverable route | "polished PDF", "one-pager", "portfolio" | Build visual deliverable and render-check | docx/pptx when editable Office file is explicit | Final format ambiguous | Not primary for editable Office files. |
| spreadsheet route | "xlsx", "spreadsheet", "formulas/charts" | Inspect tabular data and workbook target | document route | Source/columns unclear | Use workbook tools. |
| knowledge base route | "search my wiki/notes", "explain this note" | Verify target knowledge base/path, then query/summarize | web search if local source is required | Which vault/wiki/source is unclear | Path accuracy matters. |
| automation/reminder route | "remind me", "check every week", "follow up later" | Confirm exact date/time/timezone/recurrence, then create automation | calendar route when the user asks for calendar event | Ambiguous time/zone | Future actions need exact scheduling. |
| deployment route | "deploy", "publish", "share publicly" | Confirm target/env/public-vs-private if unclear, then use deploy tool | local build-only route | Production/public/cost ambiguity | External side-effect gate required. |
| git workflow route | "commit", "push", "open PR", "sync GitHub" | Inspect dirty state and remote, stage exact paths | broad cleanup route | Dirty tree or target branch unclear | Never stage unrelated files. |
| skill install/update route | "install this skill", "update this skill", "is this a skill?" | Inspect `SKILL.md`/README/source shape, install/update/hold, then sync map | generic git clone only | Source/path/secret unclear | Do not assume every repo is a skill. |
| plugin recommendation route | "which plugin should I use?", "is there a connector for this?" | Recommend one primary plugin/tool and up to two backups | executing/installing plugin | Target platform/account unclear | Recommendation is not install intent. |
| missing plugin boundary | "use Slack/Calendar/etc" when not callable | State callability boundary and recommend/request install only under install rules | pretending to use plugin | Exact plugin unavailable | Never claim a connector was used if it was not callable. |

## Ambiguity Rules

| Ambiguity | Choose | Rule |
|---|---|---|
| Recommendation vs execution | Based on verb | "Which should I use?" recommends. "Do this" routes and executes. |
| Existing fuzzy repo change vs new product | requirements clarifier vs project intake | Existing repo/change gets one funnel question; starting from scratch gets intake. |
| Editable Office vs polished PDF | Office route first | If `.docx`, `.pptx`, Word, or PowerPoint is explicit, do not route to a PDF-only workflow first. |
| Current facts vs memory | current/source route | For products, docs, pricing, law, schedules, finance, and recommendations, verify current sources. |
| Skill name as workflow vs artifact | Parse grammar | "Use X to..." activates X. "Review/edit/install/explain X" treats X as the object. |
| No dedicated match | Direct route | Say no dedicated skill is needed and execute directly. |

## Personalization Slots

Replace these with your own recurring workflows:

```markdown
### My High-Frequency Routes

| Route | User Might Say | First Action | Choose Instead Of | Ask Before | Caveats |
|---|---|---|---|---|---|
|  |  |  |  |  |  |
```

```markdown
### Hold / Do Not Recommend

| Name | Why Held | What To Use Instead |
|---|---|---|
|  |  |  |
```

```markdown
### Stale Or Dependency-Heavy Routes

| Route | Dependency | How To Verify Before Use |
|---|---|---|
|  |  |  |
```
