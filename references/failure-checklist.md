# Audience Failure Checklist

Use this checklist before publishing or changing the router. It captures why people might abandon, misuse, or complain about an intent-router skill.

| Failure Mode | Why Users Quit Or Complain | Design Mitigation In This Repo |
|---|---|---|
| Personal names and private paths leak into the public skill | Users cannot reuse it and may worry about privacy | Default map is generic and includes personalization slots only. |
| The name sounds private or vendor-specific | People do not know whether it is safe for their own setup | Public name is `intent-router`. |
| The skill promises automatic sync like a daemon | Users expect it to notice every filesystem change | README and SKILL.md say it is not a background watcher. |
| It recommends skills that are not installed | First use fails and trust collapses | `scripts/list-installed-skills.sh` helps build a local map; plugin/tool preflight is required. |
| It pretends plugins/connectors are callable | Users believe external apps were checked when they were not | Connector callability must be checked before claiming use. |
| It spends quota or deploys without approval | Users feel unsafe using the router | Cost and external side-effect gates are first-class rules. |
| It dumps the whole skill library | Output becomes a directory, not a decision | Exactly one primary route and at most two secondary routes. |
| It hides the reason for the route | Users cannot debug or trust the decision | Non-trivial turns require a visible routing note. |
| It over-asks questions | Router feels slower than doing it manually | Question Gate asks only when wrong routing has real cost. |
| It under-asks questions | Wrong route touches files, spends money, or confuses learning mode | Threshold rules require one funnel question when risk is real. |
| It treats named skills incorrectly | "Review skill X" accidentally activates skill X | Grammar rule separates workflow vs artifact. |
| It ignores read-only or recommend-only requests | Users feel it is pushy or dangerous | Safety Gate blocks file writes, installs, syncs, and external actions. |
| It cannot handle plugin vs skill vs direct execution | Users get generic advice instead of the right first action | Capability type facet separates local skill, plugin skill, connector/tool, and direct route. |
| It only works for the author's recurring workflows | Public users see irrelevant route cards | Personal route cards are templates, not bundled private examples. |
| It has no update routine | The map goes stale after new skills are installed | Router Sync Protocol records install/update/delete/disable changes. |
| It deletes skill files when the user only means "do not recommend" | Destructive behavior creates fear | Disable/hold route is separate from deletion. |
| It lacks examples and eval cases | Maintainers cannot tell whether changes broke routing | Golden eval cases cover core, docs, UI, plugins, cost, external state, and skill maintenance. |
| It fails current-fact questions from memory | Recommendations become stale | Current facts route requires current or official sources. |
| It gives an abstract philosophy but no install path | People bounce before trying it | README has direct install and configure steps. |
| It does not credit its inspiration | Users may question provenance | README and skill-map cite the EliteAI.tools `skill-router` reference. |
| Licensing is unclear | Others avoid reuse or forks | MIT license is included. |

## Pre-Publish Checklist

- [ ] No personal names, account IDs, private paths, or private project names in default files.
- [ ] `SKILL.md` frontmatter name is public and installable.
- [ ] README includes install, configure, attribution, and limitations.
- [ ] Route map is template-first and not tied to one user's library.
- [ ] Eval cases cover recommendation vs execution, read-only, plugin callability, cost, external side effects, install sync, delete vs disable.
- [ ] Scripts do not require private paths.
- [ ] The repo has a license or explicitly states reuse terms.
- [ ] Final push target is the intended GitHub repository.
