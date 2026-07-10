# Murphy Skill Map

Last synced: 2026-07-07.

This file is the router's working map. Keep it concise and decision-oriented. It does not replace each skill's `SKILL.md`; it only explains which skill to open first.

## Borrowed Pattern: Skill Router Funnel

Inspired by `sickn33/antigravity-awesome-skills/skills/skill-router` as listed on EliteAI.tools. The useful pattern is:

- short interview before recommending when the user is lost
- one primary skill plus at most two secondary skills
- exact invocation text the user can copy
- no full library dump
- pick the upstream skill first when a goal spans categories

Murphy adaptation: if Murphy asks Codex to do the task, route and execute instead of only recommending. Use the funnel only when intent or route confidence is low.

## RAG Mental Model For Routing

Think of Murphy's request as the query and this file as the retrieval corpus.

| RAG Stage | Router Equivalent | Failure To Avoid |
|---|---|---|
| Query understanding | Classify task type, output surface, risk, and whether Murphy wants execution or recommendation | Treating every request as generic "which skill?" |
| Retrieval | Pull 2-5 candidate skills or direct routes from this map | Only matching obvious words and missing intent |
| Evidence | Match candidate to trigger phrase, output format, dependency, caveat, or Murphy recurring workflow | Picking a skill with no concrete trigger evidence |
| Rerank | Choose 1 primary and at most 2 secondary routes | Dumping a chain of skills |
| Threshold | Ask one funnel question when wrong routing would waste time or touch files | Asking questions when the route is already clear |
| Generation | Say route + reason + first observable action, then recommend or execute | Giving a label without the next move |
| Eval | Compare against router eval cases after changes | Assuming the map is good because it feels plausible |

Default route card:

`我会用 <primary>，因为 <trigger evidence>; first action: <next step>。`

Default visible route card:

`分诊过程：<cue> -> 候选为 murphy-skill-router, <A>, <B> -> 选择 <primary/direct> 因为 <reason>; 未用 <candidate-1>/<candidate-2> 因为 <rejected reasons>; first action: <next step>。`

Always include `murphy-skill-router` as one visible candidate in every routed turn. It is the meta-route being applied, even when it is not the selected primary route. Trivial direct answers may use a short note, but the note still includes `候选为 murphy-skill-router`.

Evidence fields to maintain for high-frequency or newly corrected routes:

```yaml
positive_cues:
anti_cues:
first_action:
dependencies:
choose_instead_of:
eval_ids:
```

Do not expand every row into a large schema unless needed. Add evidence fields first where routing has failed, where skills overlap, or where a dependency/caveat can waste Murphy's time.

## Global Router And Maintenance Rule

This map is Murphy's global personal route map for skills, plugins, connectors, apps, and direct tool routes. It is not limited to the current `cwd`.

It is not a background watcher. It only updates automatically when Codex participates in, or is told about, a skill install/update/delete/disable/check flow.

After every skill install, update, rule/config change, delete, disable, or "is this a skill?" inspection:

1. Add or update the skill entry below without requiring Murphy to separately say "sync router".
2. Add overlap notes if it resembles an existing skill.
3. Record dependencies and caveats, especially missing CLIs, stale paths, or restart requirements.
4. Record plugin/connector/tool dependencies and paid/external side-effect gates when relevant.
5. If Murphy says a skill should not be recommended but does not explicitly request deletion, demote or hold the route; do not delete files.
6. If Murphy explicitly requests deletion/removal, verify exact skill name, absolute path, and delete scope before destructive action; after deletion, update the map.
7. If the repo is not installed because it is not a Codex skill, add it under "Hold / Not A Codex Skill" when it may be confused with one later.
8. Run or mentally compare against `references/router-eval-cases.md` for affected areas.

## Plugin, Connector, Cost, And Side-Effect Rules

| Situation | Route | Rule |
|---|---|---|
| Plugin/tool appears relevant | Plugin/connector preflight | Check whether a callable tool exists in this session; use `tool_search` when available before falling back. |
| Tool is callable | Execute via plugin/app/tool route | Still show visible routing note and dependency caveats. |
| Tool is not callable | Recommendation or install-boundary route | Do not pretend it was used; recommend it or request install only when Murphy explicitly asks for that exact known installable plugin/connector. |
| User asks "which plugin?" | Guided recommendation mode | Recommend; do not install or execute. |
| OpenAI API / metered API / image/audio/video generation | Cost gate first | Having a key is not spending approval; state scope/quota/cost risk and ask before first paid/quota-consuming call. |
| Vercel deploy / send email / write Drive/Notion/calendar / create automation / publish/share | External side-effect gate first | Confirm target/account/env/public-vs-private details when unclear or risky. |
| Read-only review | No write/call/install route | Report what would be done; do not mutate router, external state, or files. |

## Murphy Recurring Workflows

| Workflow | Route First | First Observable Action | Caveat |
|---|---|---|---|
| Learning session / "先不要写代码" / "按昨天节奏" | Learning-mode behavior, not implementation skills | Ask one prediction question or give one tiny task | Do not jump ahead or code unless Murphy switches mode. |
| Hello-Agent / Agentic RAG study | `stepwise-agent-tutoring`; then `obsidian-markdown` only for note format | Verify exact repo/vault path and current day/topic | Keep notes durable; preserve user attempt + corrected version. |
| RAG concept comparison | Direct explanation with RAG stage separation | Separate query translation, routing, construction, indexing, retrieval, rerank, evidence, generation | Do not blur rewrite/search/rank/check. |
| Practical travel/shopping/local planning | Direct execution; use browsing/current sources when prices/routes/hours matter | Gather constraints and current facts, then produce route/budget | No dedicated skill exists yet; do not force market research. |
| School/admission/ranking tracking | Direct execution plus current-source verification | Verify dates/status/rank source before advising | Treat as time-sensitive and high-stakes. |
| Calendar/reminder/follow-up | Automation/calendar route if available; otherwise local verified flow | Confirm exact date/time/timezone and duplicate risk | Use automations for recurring or future follow-up. |
| macOS/local file operation | Direct cautious execution | Verify exact scope before destructive or privacy-sensitive actions | Never broaden deletion/staging. |
| Read-only review / product audit | Review stance; no write route | Inspect and report findings, tests, and suggested changes | Do not sync, install, edit, stage, commit, or write files. |
| Skill install/update/check | skill-install route, then automatic `murphy-skill-router` sync | Inspect skill shape, use available installer skill/script if present, install/update/hold, then update map without requiring a second prompt | Do not rely on stale installer names; mention map sync status and restart caveat in final. |
| Skill delete/disable | Explicit delete/disable route, then router sync | Verify exact target and intent, delete only when explicitly requested, otherwise demote/hold recommendation | Deletion is destructive; "不用了" is not deletion authorization. |
| Not-a-skill cleanup / hold route | Direct cautious cleanup, then optional hold note | Verify exact deletion target; if useful, add Hold / Not A Codex Skill note | Clarify path before deletion unless target is already explicit. |

## Ambiguity Rules

| Ambiguity | Choose | Rule |
|---|---|---|
| Recommendation vs execution | Based on Murphy's verb | "用什么 skill" recommends; "帮我处理/做/改/查" routes and executes. |
| Router named as meta-route | downstream primary, not `murphy-skill-router` | When Murphy says to use the router and also gives a real task, keep `murphy-skill-router` visible as the routing pass but choose the task skill/plugin as primary. Only choose router itself for router maintenance, route recommendations, evals, install/update/delete/disable sync, or explaining routing. |
| Broad unclear redesign / rethink / high-risk automation | `superpowers:brainstorming` | If cues include "垃圾", "重做", "重新搜索", "别人项目基础上", "个性化", "可验证", "可迭代", "进化", "核心需求", "修改方向", "前瞻性", "预定时间", "定时任务", first clarify design and success criteria before search, implementation, trading, deployment, or scheduling. Domain routes become secondary. |
| Existing fuzzy repo change vs new product | `quick-requirement-clarifier` vs `project-intake-interview` | Existing repo/change gets one funnel question; starting from scratch gets intake. |
| `docx` vs `kami` | `docx` when Word is required | If `.docx` or Word is explicit, choose Word route first even if polish is requested. |
| `pptx` vs polished PDF | `pptx` when editable deck is required | If PowerPoint/editable slides are explicit, do not route to Kami first. |
| WiKi vs Obsidian | Path/context decides; otherwise ask one location question | WiKi repo uses wiki skills; Obsidian file syntax uses Obsidian skills. |
| `diagnose` vs `debugging-and-error-recovery` | `diagnose` for non-obvious/hard bugs | Pick one; use Superpowers debugging only when explicitly requested or strict discipline is needed. |
| Frontend design vs UI engineering | `frontend-design` for look/feel; `frontend-ui-engineering` for component behavior | If user says "丑/廉价/上线感", design leads. If state/accessibility/responsive bug, UI engineering leads. |
| Current facts vs memory | Current official/source check | For products, prices, laws, docs, schedules, rankings, and recommendations, verify live/current sources. |
| Skill map match vs no dedicated skill | Direct execution | If no skill cleanly fits, say so briefly and do the work. |
| Skill name as workflow vs artifact | Parse grammar | "用 X 做..." activates X; "评估/修改/安装/解释 X" treats X as the object. |

## High-Frequency Route Cards

Use these cards for common Murphy phrasing. They do not replace the full rows below; they make first actions and anti-cues explicit.

| Skill / Route | Murphy Might Say | First Action | Choose Instead Of | Ask Before | Caveats |
|---|---|---|---|---|---|
| `futu-supervisor-closer` | "跑一下 Futu adaptive supervisor", "daily_health 还是 stale", "把 stale packet 关掉", "财务自动化健康吗", "低频量化 supervisor" | Inspect `reports/scheduler/YYYY-MM-DD.json` plus `data/scheduler/adaptive_tasks.jsonl`, then close existing non-entry task IDs until healthy or a named external blocker remains | `futuapi` for brokerage/account/API operations; generic automation edits | Repo/date or whether user wants read-only report vs closure unclear | SIMULATE-only, non-entry by default; use `TZ=UTC`; do not create broker-facing follow-ups. |
| `codex-network-lifeline-diagnoser` | "GitHub 开 VPN 就打不开", "FIClash", "FlClash", "DNS 污染", "Codex 断网", "小火箭", "代理慢" | Gather read-only OpenAI/GitHub/proxy/Wi-Fi/DNS evidence and identify rollback before any proxy/VPN mutation | generic browser debugging, broad system-network changes | Mac vs phone surface or write permission/rollback unclear | Treat VPN/proxy as Codex lifeline; read-only first; writes require reachability and rollback. |
| `interview-portfolio-evidence-packager` | "帮我准备项目1面试", "整理作品集", "讲 CodeHarness", "简历项目", "AI engineer interview", "Enterprise DataCopilot 怎么讲" | Inspect the smallest repo/resume/eval evidence, then package problem -> architecture -> constraints -> evidence -> follow-up defense | `interview-officer` for live mock interview; generic resume polish without evidence | Target audience, role, or source artifact unclear | Do not invent metrics or production claims; keep LLM/tool/human-confirmation boundaries explicit. |
| `notion-morning-evidence-coach` | "晨间导师督导", "今天晨间导师", "No Evidence 恢复计划", "日记督导", "每日计划", "给我今天主线" | Fetch/inspect yesterday journal and plan evidence; if missing, emit `No Evidence` and one-main-line recovery plan | generic Notion read/spec routes, broad productivity advice | Target day/database or read/write intent unclear | Keep Notion as database and Codex as reasoning layer; do not invent progress or overbuild the hub. |
| `quick-requirement-clarifier` | "这个 repo 想加功能但我说不清", "你帮我理一下需求" | Ask one funnel question | `project-intake-interview` for new products | Only if cheap file inspection cannot resolve | Do not over-interview. |
| `project-intake-interview` | "从零做一个项目/网站/工具", "我有个想法" | Ask first product/context question | `quick-requirement-clarifier` for existing scoped changes | Missing audience/output/platform | Good for starting from scratch. |
| `superpowers:brainstorming` | "先头脑风暴", "核心需求和修改方向", "重做/重新设计", "重新搜索并在别人项目基础上完善", "个性化/可验证/可迭代/进化系统", "复杂系统先想清楚", "自动化量化系统做得垃圾", "低频交易/前瞻性/预定时间/定时任务购入" | Inspect smallest context, then ask one clarifying question before solution search or implementation | `futuapi`, Public Equity Investing, Automations, `spec-driven-development`, `incremental-implementation` when direction is not approved | If user explicitly says skip brainstorming and gives exact implementation contract | Use as upstream design gate; domain/action routes become secondary follow-ons. For finance/trading, keep SIMULATE/no-real-money and external side-effect gates. |
| `diagnose` | "不要猜", "偶尔报错", "线上 500", "查清楚根因" | Reproduce, inspect logs, form hypothesis | `debugging-and-error-recovery` for straightforward errors | Only if target service/log path unknown | Pick one debugging workflow. |
| `debugging-and-error-recovery` | "这个命令报错", "测试挂了", "构建失败" | Read exact error and run smallest repro | `diagnose` for hard intermittent bugs | If write scope or repro command unknown | Broad recovery workflow. |
| `incremental-implementation` | "需求已经明确", "按薄切片实现", "一小步一小步改", "实现并加测试" | Pick the smallest vertical slice and pair with tests | `quick-requirement-clarifier` when requirements are fuzzy | If acceptance behavior is missing | Use after upstream design/clarification is done. |
| `tdd` | "严肃实现这个 bug/feature", "先红绿重构" | Write failing behavior test first | `test-driven-development` when Addy lifecycle is explicitly preferred | If no behavior surface is known | Strong Matt Pocock test shape. |
| `code-review-and-quality` | "review 这次改动", "只看 bug/回归风险/缺少的测试", "代码审查" | Inspect diff and lead with findings | implementation routes | If no diff/files are available | Review stance; do not edit unless Murphy asks. |
| Murphy router self-evolution route | "router 长期自进化", "自动晋升", "保留 baseline", "候选 patch", "回滚 router", "evolution gate", "让分诊越来越懂我" | Use `references/evolution-log.jsonl` -> synthesize pending cases -> create candidate -> run `scripts/evolution_gate.py --suite all` -> promote only after gate passes | generic skill install/update route or direct map edits | If Murphy asks read-only evaluation only | Baseline is immutable; logs are desensitized summaries; guard-script changes require human review. |
| `setup-matt-pocock-skills` | "配置 mattpocock/skills", "这个 repo 先接入 Matt skills", "这些 skill 缺上下文" | Inspect repo tracker/docs, then write/update `AGENTS.md` or `CLAUDE.md` plus `docs/agents/*` | generic skill install route after skills are already installed | If no `AGENTS.md`/`CLAUDE.md` exists and creating one is not obvious | Per-repo config, not global install. Default GitHub if repo remote is GitHub; otherwise local markdown is okay for solo/temp work. |
| `to-prd` | "整理成 PRD", "把上面对话变需求文档", "沉淀产品需求" | Explore current repo context, confirm major modules/test targets, then publish PRD to configured issue tracker | `spec-driven-development` when no issue-tracker publishing is wanted | If repo has not run `setup-matt-pocock-skills` | Do not interview broadly; synthesize known context and use domain glossary/ADRs. |
| `to-issues` | "把 PRD 拆任务", "拆成可领取 issue", "拆 AFK/HITL 实现票" | Read PRD/plan, draft tracer-bullet vertical slices, then ask user to approve granularity | generic planning-and-task-breakdown | If source PRD/path is missing and conversation lacks enough plan | Issues should be independently verifiable vertical slices, not layer-by-layer horizontal tasks. |
| `triage` | "分诊 issue", "ready-for-agent", "needs-info", "wontfix", "哪些票能给 agent 做" | Fetch referenced issue(s), apply exactly one category and one state role per issue | code-review or planning routes | If label mapping or issue tracker config is missing | Comments posted to tracker need the AI-triage disclaimer. |
| `grill-me` | "拷打我的方案", "grill me", "追问这个设计" | Ask one decision-tree question at a time, with recommended answer | `grill-with-docs` when repo glossary/ADR should be updated | If the plan/code context is absent and first question would be blind | Interview workflow, not implementation. |
| `grill-with-docs` | "结合 CONTEXT/ADR 拷打方案", "把术语/决策沉淀到 docs" | Read `CONTEXT.md`/ADRs, question one branch at a time, update docs as decisions crystallize | `grill-me` for no-doc/no-repo brainstorming | Before writing docs if user asked read-only | Use when language and decisions must become durable. |
| `zoom-out` | "我不熟这块代码", "给我上一层视角", "这部分怎么串起来" | Map relevant modules, callers, and domain terms before proposing changes | implementation/refactor route | If user already gave a tiny direct edit | Explanation-first route. |
| `frontend-design` | "页面廉价/不好看/不像产品/上线感" | Inspect current UI and screenshot target | `frontend-ui-engineering` for behavior/accessibility/state | If no app URL/path exists | Verify visually after changes. |
| `frontend-ui-engineering` | "组件交互/响应式/状态/可访问性有问题" | Inspect component files and UI state | `frontend-design` for visual polish | If unclear whether issue is visual or behavioral | Pair with Browser/Chrome when running locally. |
| `open-design-assistant` | "打开 Open Design", "进入设计模式", "用 Open Design 画布", "读取/修改当前设计稿", "当前设计稿", "设计稿", "产品原型", "localhost:64392" | Check both `tools-dev status` and `curl -I http://127.0.0.1:64392/`, open the local canvas, then use `.od/projects` / `.od/artifacts` as shared files | Browser-only route when design/file collaboration is needed; `frontend-design` when no Open Design canvas is involved | If the active project/file is ambiguous or a new generation would spend agent quota | The status command may say `not-running` while HTTP is live; local open/read/edit is safe, but new Open Design generation may consume quota. |
| Browser / Chrome plugin route | "打开 localhost", "帮我看页面", "点一下", "截图验证" | Open in-app Browser or Chrome target | `playwright` for scripted repeatable flows | If target URL/port missing | Prefer Browser for explicit localhost/open/click requests. |
| `openai-docs` | "OpenAI API/模型/价格/Agents 最新怎么用" | Use official/current OpenAI sources | memory answer | If the user asks opinion only and docs are irrelevant | Separate official confirmation from inference. |
| `openai-developers:agents-sdk` | "用 OpenAI Agents SDK 做 demo/agent", "OpenAI Agents SDK 最新怎么用", "看官方文档" | Read Agents SDK skill/docs first | generic `openai-docs` alone | If API key/setup state unknown | Use official OpenAI flow; do not invent APIs. |
| `openai-developers:openai-platform-api-key` | "帮我配置 OPENAI_API_KEY/sk-proj" | Use secure key setup flow | manual pasted-key instructions | If Codex secure flow unavailable | Never ask Murphy to paste secrets in chat. |
| `docx` / `doc` | "Word 版", ".docx", "能交的报告" | Inspect prompt/content and draft Word artifact | `kami` when editable Word is required | If identity/rubric/source missing | For academic work, use rubric-first support. |
| `pptx` / `pptx-skill` | "可编辑 PPT/PPTX", "PowerPoint" | Create/edit deck as `.pptx` | `kami` when editable deck is required | If audience/slide count missing | Verify rendered slides when possible. |
| `kami` | "好看的 PDF/一页纸/作品集/视觉交付物" | Build polished visual deliverable | `docx`/`pptx` when editable Office format is explicit | If final format is ambiguous | Not primary for editable Office files. |
| `wiki-query` / `wiki-explain-page` | "在 WiKi 里查/解释", path under `<WIKI_REPO_PATH>` | Verify WiKi repo path and query | Obsidian skills | If user says "知识库" without path | Use WiKi skills for WiKi project. |
| `obsidian-markdown` | "写成 Obsidian 笔记/属性/双链/callout" | Verify target vault/path if writing | WiKi skills when in WiKi repo | If vault/path unclear | File-format skill; no live app needed. |
| `start-my-day` | "start my day", "今天/每日 arXiv 论文推荐", "最近有什么论文值得读", "帮我生成论文推荐到 Obsidian" | Verify `OBSIDIAN_VAULT_PATH` and `99_System/Config/research_interests.yaml`, then run the daily paper recommendation workflow | `aihot`, generic web search, `paper-search` | If vault path/config is missing | Writes Obsidian daily notes, uses arXiv/Semantic Scholar network calls, and may call `paper-analyze`/`extract-paper-images` for top papers. |
| `paper-analyze` | "分析这篇论文", "读一下 arXiv:2402.12345", "生成图文论文笔记", "深度读论文" | Resolve arXiv ID/title and vault config, then generate a structured paper note with images | `wiki-explain-page`, generic summary, `obsidian-markdown` alone | If target paper or vault path is unclear | Best for Obsidian paper notes; choose WiKi skills only when the target is the local WiKi repo. |
| `paper-search` | "搜我已有论文笔记", "Obsidian 里有没有某篇论文/作者/关键词" | Search `20_Research/Papers/` in the configured vault | web search, arXiv search, `wiki-query` | If the target knowledge base is WiKi vs Obsidian unclear | Searches existing notes only; it is not a live literature search. |
| `conf-papers` | "搜 2025 ICLR/NeurIPS/CVPR 论文", "顶会论文推荐", "今年顶会 LLM/agent 论文", "ICLR 里 agent 方向值得读" | Verify year/conference and config, then use DBLP + Semantic Scholar ranking | `start-my-day`, generic arXiv search | If year/conference or vault write target is unclear | Writes an Obsidian recommendation note; papers without arXiv IDs cannot be auto-image-extracted/deep-analyzed. |
| `extract-paper-images` | "提取论文图片", "把 arXiv/PDF 里的图拿出来", "论文图不对/都是 logo" | Resolve paper ID/PDF and output note image directory, then extract from arXiv source before PDF fallback | image generation skills, `paper-analyze` as primary | If output note/domain path is unclear | Auxiliary route for paper-note images; requires PyMuPDF/requests and network for arXiv source packages. |
| Learning-mode route | "第 0 步", "先不要写代码", "教我/面试我/检查我理解" | Ask one prediction question | implementation/planning skills | If topic/source is unclear | One tiny task, then stop. |
| Automations route | "提醒我", "每天/每周检查", "到时候叫我" | Use automation tool with exact date/time/timezone | local calendar if user asks calendar event | Ambiguous recurrence/timezone | Prefer heartbeat for same-thread follow-up. |
| App connector routes | "查 Gmail/Outlook/Drive/Notion/Linear/GitHub", "过去一天重要邮件", "垃圾箱和 spam 不算", "inbox/unread" | Use matching plugin/app tool if callable; otherwise run plugin preflight/recommendation route | generic web/search | If connector not installed or target account unclear | Do not ask to install unless user explicitly requests a listed connector. |
| Plugin recommendation route | "应该用哪个插件", "有没有插件能处理这个" | Recommend one primary plugin/skill and at most two backups | executing/installing the plugin | Missing target platform | Recommendation intent is not install or execution intent. |
| Superpowers plugin install/check route | "下载 superpower 插件", "装 Superpowers", "为什么 Superpower 下不了" | Check local plugin config/cache first; canonical Codex plugin name is `superpowers` and enabled installs expose `superpowers:*` skills | adding `superpower@...` as an alias; reinstalling when already enabled | If config/cache missing or current app inventory has not refreshed | Treat singular `superpower` as a natural-language alias only; do not create invalid plugin config keys. |
| Public Equity Investing plugin route | "炒股", "股票研究", "美股投研", "分析某只股票/ETF", "财报/估值/催化剂" | Use Public Equity Investing when callable, and verify current filings/prices/news before analysis | `futuapi` for live Futu account/order/API actions; `lishu-serenity` for narrative supply-chain thesis writing | Ticker, market, time horizon, research-only vs trade execution unclear | Research aid only; high-stakes/current facts require source checks and no direct buy/sell advice. |
| Data Analytics / Spreadsheets plugin route | "分析我的持仓/交易记录/收益回撤", "做股票跟踪表", "生成 dashboard/表格" | Use Data Analytics for analysis/report dashboards; use Spreadsheets for editable workbook outputs | Public Equity Investing when the main ask is company thesis/research | Data file/location/output format unclear | Keep snapshots bounded; private trading data is sensitive. |
| Investment Banking plugin route | "投行视角", "并购/估值模型/可比公司/DCF/资本市场" | Use Investment Banking for transaction, valuation, pitch, or diligence workflows | Public Equity Investing for public-market stock thesis and catalysts | Deal context/company/set of comps unclear | Not the default for daily trading research. |
| Product Design / Creative Production plugin route | "产品原型/设计探索/广告素材/营销图/活动创意" | Use Product Design for product prototypes and user flows; Creative Production for ads, moodboards, logos, shots, offers | `frontend-design` for local app UI implementation | Target channel/brand/assets unclear | Creative tools may generate visible artifacts; ask before external publishing. |
| Documents / Presentations plugin route | "做 Word/文档", "做 PPT/slide deck", "改演示文稿" | Use Documents for document artifacts and Presentations for slide decks when plugin workflow is a better fit | local `docx`/`pptx` skills for file-first local Office outputs | Editable format, source files, and destination unclear | Do not upload/share externally without explicit target approval. |
| Missing plugin boundary route | "用 Slack/Teams/Calendar 插件查...", but tool is not callable | State unavailable/callability boundary, then recommend/request install only under install rules | pretending to call the plugin | If exact plugin is unavailable or not known installable | Use `request_plugin_install` only for explicit exact install requests and known installable entries. |
| OpenAI paid API approval route | "用 OpenAI API 跑 embedding/生成图/语音/视频", "调用 sk-proj" | Estimate scope when cheap, state quota/cost risk, ask approval before first paid call | running API immediately | Missing key, model, budget, or scope | API key presence is not spending approval. |
| External side-effect route | "部署到 Vercel", "发邮件", "写日历", "发到 Notion/Drive", "公开分享" | Confirm target/account/env/public-vs-private if unclear, then use plugin/tool route | local-only answer or silent external mutation | Production/public/cost ambiguity | Explicit user action grants intent, not missing details. |

## Murphy High-Frequency Supplemental Route Cards

These cards come from recent memory evidence. They are the first place to check when Murphy's phrasing matches a recurring project/workflow. Many are direct routes because forcing a dedicated skill would make routing worse.

| Skill / Route | Murphy Might Say | First Action | Choose Instead Of | Ask Before | Caveats |
|---|---|---|---|---|---|
| `stepwise-agent-tutoring` | "我现在在做什么", "今天 RAG 学到哪了", "继续昨天的 Agent/RAG", "第 0 步", "先不要写代码" | Verify inner repo `tutorial-hello-agents/Co-creation-projects/murphy-CodeAgentIntern`, then inspect `learning-log/progress.md`, `NEXT_STEPS.md`, templates, and git root | generic learning route, outer hello-agent path | If lesson vs status summary is unclear | Start with repo-grounded state, one prediction/checkpoint, and durable notes. |
| `stepwise-agent-tutoring` + exact git route | "同步到云端让我看到掌握程度", "沉淀 notes", "不要只在聊天里总结" | Read `notes/templates/`, update progress/dashboard or note artifacts, run `git status --short`, then exact commit/push if requested and clean | code-only git sync | Dirty tree, private/public remote, or excluded material unclear | GitHub should show learning progress and mastery, not code alone. |
| `stepwise-agent-tutoring` for Agentic RAG implementation/eval | "先做真实 embedding retrieval", "Gold Evidence", "RetrieverEvalCase", "retriever eval" | In learning mode ask one prediction question; in implementation mode build retrieval/eval foundation before light Agent integration | big rewrite of `CodeAgent.analyze`, generic TDD | API key/setup missing, or teaching vs implementation unclear | `.env` is one level above repo; eval starts with `recall@k`, `evidence_hit`, and `range_exact`. |
| `hermes-control-gate-audit` | "Hermes 进度怎么样", "PAUSE 能不能清", "为什么还没动", "BLOCK_WAITING_MURPHY", "NO_CODEX_LAUNCH", "废站武器库挂载到 hermes" | Inspect live control files, board/card state, worktree evidence, worker/automation liveness, then classify blockers and safe actions | generic status summary, direct repo edits, dispatch automation | Any writeback, unblock, dispatch, PAUSE clear, or repo edit | Read-only by default; use buckets like `must_fix_before_dispatch`, `safe_readonly_actions`, `safe_comment_only_actions`, and `do_not_run_yet`. |
| `yao-weread-skill` | "分析微信读书历史", "近三年读书报告", "生成读书报告/画像/HTML/图表" | Read local skill docs/config, then build report/visualization route | `weread-skills` for raw lookup or capability boundary questions | Time range/account/report format unclear | Depends on `weread-skills` data/API assumptions; do not use as primary for "能不能读正文". |
| `weread-skills` | "查微信读书书架/笔记/进度", "微信读书 skill 能不能直接读正文", "能读整本书吗" | Read local docs and answer exact capability boundary before claiming access | `yao-weread-skill` report route, generic web/search | Account/API access unclear | Raw lookup/capability route. Do not claim whole-book正文 reading unless local docs and tool output prove it. |
| `resume-optimizer` | "简历优化", "简历诊断", "简历改写", "投递前帮我看简历", "根据项目经历优化 AI 应用实习简历", "保留真实证据" | Inspect resume/JD, find highest-impact issues, then rewrite with evidence and placeholders for missing metrics | `resume-backend-project-optimizer` for backend bullet rewriting; `resume-interview-coach` for interview defense | Target JD, role, or source resume unclear | Do not invent metrics or finished work. |
| `resume-backend-project-optimizer` | "把后端项目经历改成简历 bullet", "Java 后端项目怎么写", "按技术细节+数据化结果改写" | Convert backend project descriptions into quantified, interviewable Chinese resume bullets | generic `resume-optimizer` for whole-resume audit | Project facts/metrics missing | Keep frontend out; use placeholders for unknown metrics. |
| `resume-interview-coach` | "这段项目面试会怎么问", "帮我准备项目追问", "STAR 话术", "简历防御" | Diagnose scenario, ask hard backend interview questions, then build STAR answers and defense points | `resume-optimizer` when the goal is resume text first | Role/project context unclear | Coach for interview readiness, not evidence fabrication. |
| `interview-officer` | "模拟面试", "面试官视角", "拷问我的项目", "项目追问", "你站在面试官角度听什么" | Act as a strict interviewer, ask one question at a time, grade answers, and force problem/metric/system/tradeoff/risk/evidence/ownership clarity | `resume-interview-coach` for STAR script and resume-defense packaging | Project or interview target unclear | Do not fabricate metrics or production claims; mark missing evidence as pending. |
| `resume-template-from-image` | "照这张简历模板图生成模板", "新增一个简历模板", "按图片做 resume template" | Require template name, then implement the existing resume-template project file structure and registration | generic frontend/image-to-code route | Template name or target resume app repo unclear | Project-specific; only use where the resume template architecture exists. |
| `shushu-internship-tool` | "鼠鼠实习", "给这个 JD 找项目", "实习项目怎么准备", "项目改造成能投简历/面试" | Run concise intake, then find/audit GitHub projects, choose run path, write resume bullets and interview Q&A | generic resume skills when no project/JD discovery is needed | JD, user level, time budget, or run depth unclear | Prioritize interview-ready project material over full research reproduction. |
| `futuapi` | "富途行情", "Futu API", "查 K 线/报价/期权链/持仓/订单", "模拟盘", "不要真下单", "下单/撤单" | Check OpenD/SDK readiness, default to simulated trading, then use Futu OpenAPI patterns | Public Equity Investing for source-backed stock research without account/API operations | Real trading environment, account, symbol, or permission unclear | Real-money trading requires explicit approval; never default to live orders. |
| `install-futu-opend` | "安装/启动/配置 OpenD", "升级 futu-api", "富途开发环境" | Detect OS, install or guide OpenD setup, and upgrade/check Python SDK | `futuapi` after OpenD and SDK are ready | Download path or admin/install permission unclear | Network/download and local installation can mutate system state. |
| `lishu-serenity` / `serenity-supply-chain-thesis` | "用 Serenity 风格分析", "AI 光通信/CPO/半导体小票", "供应链瓶颈 thesis", "稀释风险" | Open the workspace-local skill and write a bounded supply-chain thesis with catalysts, valuation asymmetry, and invalidation signals | Public Equity Investing for broader current-source public-market research; `futuapi` for live brokerage/API actions | Ticker, timeframe, or research-only boundary unclear | Installed under current workspace `skills/lishu-serenity`, not global `~/.codex/skills`; not financial advice and source freshness must be checked. |
| Direct: standalone skill install/config route | "下载这个 ZIP/网页安装 skill", "这个 HTTPS skill 页面装一下", "写入配置并验证" | Inspect `SKILL.md`, `install.sh`, README, or archive root; then install/configure/verify if real skill | GitHub-only assumptions, stale `skill-installer` name | Secret/network/write path unclear | Do not echo secrets; read-only tasks do not sync map. |
| `aihot` + Automations route | "工作日每天十点 AI 日报", "现在也想看 AI 热点" | Verify `aihot` standalone skill/API, then create HKT weekday heartbeat with same-day dedupe; manual digest can run immediately | generic reminder or generic news answer | Timezone, destination, or frequency unclear | Weekends and duplicate same-day runs should not notify unless Murphy asks. |
| Direct: email triage automation | "刷邮箱", "10 点 22 点看 Outlook 未读重要邮件", "学校有没有邮件" | Use available email connector; if Outlook is unavailable and Murphy authorizes, switch to Gmail | generic app connector row, web search | Provider/account/scope unclear | Privacy-sensitive; report important mail, not full inbox dump. |
| Direct: chained thread heartbeat | "80 分钟后提醒休息，再 15 分钟后学习", "到时候继续这个线程" | Check current date/time/timezone, then use a thread heartbeat and update chain after wake-up | Apple Calendar / macOS Reminders | System-level reminder vs thread follow-up unclear | Current thread heartbeat is the right default for same-thread continuation. |
| Direct: Apple Calendar dedupe write | "仿照之前的日程", "当天重复就不用加", "加到日历" | Query writable calendars and narrow date range, copy existing event shape, skip same-title same-day duplicates | Automations route | Calendar/date/time/title unclear | AppleScript dates should be component-built to avoid locale errors. |
| Direct: macOS cleanup/uninstall audit | "删除这个软件和相关文件", "哪些可以删", "清理本机" | Audit first, classify `safe / confirm / do not touch`, then ask before destructive groups | `neat-freak`, broad deletion | Confirm-group deletion or personal files | Prefer Trash; permission errors may be normal macOS noise. |
| Direct: mixed-worktree recovery | "docs-only 提交", "不要 git add -A", "recovery branch", "精确 staging" | Inspect full dirty/untracked state, classify safe/excluded groups, then stage exact paths only | generic git workflow | Commit/push/PR target unclear or evidence files overlap | Never revert unrelated changes; preserve excluded evidence/assets. |
| Direct: gameplay/readability route | "武器是主要乐趣", "HUD 可读性", "telegraph", "废站武器库" | Classify gameplay tuning vs UI-only vs report-only, then inspect relevant files/tests | generic frontend-design/ui-engineering | Source edit vs report-only, e2e port permissions | Do not drift into unrelated UI overhaul. |
| Direct: generated_actor_atlas phase gate | "Phase 4AE", "generated_actor_atlas", "worker lane", "sprite atlas" | Verify cwd, phase, ledger, schema, and runtime-ready status before any asset generation/pack/promote/wire | sprite generation by default | Any asset generation or mainline wiring | Placeholder atlas is not a complete contract; mainline/worker boundaries matter. |
| Direct: Hong Kong local shopping route | "香港伴手礼", "500 预算", "文青复古", "一次买齐", "别太游客" | Confirm constraints, verify current official/shop pages, then output route + budget | `market-landscape-researcher` unless broad comparison is needed | Recipient/budget/classic-food preference unclear | Phrase "内地没有卖" carefully; exclude tea if Murphy says no tea. |
| Direct: admissions/ranking status route | "NUS/NTU/HKU 状态", "PolyU QS top 50 概率", "申请怎么样了" | Verify current portal/email/official ranking source, then give status and bounded scenarios | memory-only answer, generic career advice | Login/connector/sending update emails unclear | Time-sensitive and high-stakes; avoid single-point certainty. |
| `openai-docs` + quota/model route | "5.5 vs 5.4", "同样额度更多还是更少", "推理强度怎么选" | Check official OpenAI/Codex docs or current rate card, then separate official confirmation from inference | memory-only model comparison | ChatGPT/Codex/API scenario unclear | Capability and quota efficiency are separate axes. |
| `openai-docs` / OpenAI API paid route | "用 OpenAI API 生成/embedding/语音/视频", "Responses API 实跑一下" | Verify official docs and local key path, then run cost gate before paid/quota call | memory-only answer, immediate API spend | Scope/budget/key/model unclear | Use secure key setup; never ask for pasted secrets. |
| Vercel plugin route | "用 Vercel 插件部署", "查 Vercel build log", "Vercel pricing/docs" | Use Vercel tools/skills when callable, then external side-effect gate for deploys | generic deployment advice | Project/team/env/production target unclear | Docs search is read-only; deploy mutates external state. |
| Google Drive connector route | "去 Google Drive 找/上传/创建 Docs/Sheets/Slides" | Use Google Drive plugin/app tool when callable | web search, local filesystem search | Account/folder/write target unclear | Upload/create/write actions are external side effects. |
| `notion:notion-research-documentation` / Notion read route | "查 Notion", "Notion 里最新内容", "先不要写计划" | Search/open Notion source and summarize or cite current content | `notion:notion-spec-to-implementation`, generic planning | Page/database/workspace target unclear | Read/search is not implementation planning; do not convert to a plan when Murphy says "先不要写计划". |
| `notion:notion-spec-to-implementation` | "把 Notion spec 变实现计划", "根据 Notion 规格做开发计划" | Fetch the spec, then produce an implementation plan/tasks | Notion read route | Page/spec target unclear | Use only when Murphy asks to turn Notion content into implementation work. |
| Notion write/capture route | "写入 Notion", "保存到 Notion", "记录到 Notion" | Confirm destination page/database, then apply external side-effect gate | read-only Notion route | Destination/database unclear | Writing Notion mutates external state. |
| `assignment-support-coach` + `docx` | "老师角度评分", "A+ 水准", "Word/PDF 能交", "rubric" | Reconstruct rubric/marker view first, ask one clarification at a time, then verify identity fields and export | `docx` alone, `kami` | Brief/rubric/identity/source evidence missing | Respect academic integrity; course-facing writing may need English. |
| Direct: course cheatsheet DOCX | "EIE4102 Test2 优先", "tutorial 7/8/9", "越多越好", "cheatsheet" | Verify source materials and generator/deps, produce Word by exam-priority order, validate `.docx` if preview unavailable | generic `docx`, assignment coach | Exam scope/order unclear | Preserve figure-heavy content; handle missing docx dependencies first. |
| Direct: ShanghaiRanking merged Word | "211 排名", "全国排名", "港澳台交叉比对", "只要 Word" | Verify current payload/source, distinguish `rankOverall`, and generate one DOCX with method notes | chat summary, market research | Official rank vs reference position unclear | 港澳台 inserted positions must be labelled cross-estimated/reference. |
| `wiki-ingest` / `wiki-lint` | "更新 WiKi", "导入论文", "看到知识图谱", "更新知识库" | Verify WiKi path, then source -> concept/entity/synthesis -> index/log -> link check | Obsidian markdown, wiki-query only | Source type or target page unclear | Keep `raw/` immutable; trust content over filename. |
| `wiki-explain-page` refined | "讲解这个新论文", "内容干瘪", "不要如果你愿意结尾" | Locate exact wiki page and learner profile, then explain by material type | generic external summary, memory-only answer | Target ambiguous, e.g. "新 DeepSeek" | Define terms before use; avoid invitation-style endings by default. |
| `wechat-miniapp-preflight-review` / direct orientation | "这是个什么项目", "花识图鉴", "微信小程序", "发布前检查" | Inspect README/app config/cloudfunctions, then explain product purpose, demo/cloud mode, and release risks | generic frontend route | Cloud mode/API key/release QA unclear | Miniapp frontend/cloud-function boundary should be stated early. |

## Meta And Routing

| Skill | Use First When | Notes |
|---|---|---|
| `murphy-skill-router` | Murphy asks "which skill/plugin/tool", "自动判断", "帮我分诊", or multiple installed skill/plugin families would materially change the next action | Global personal router. Also auto-sync this map after Codex participates in skill install/update/rule changes or explicit delete/disable flows. Do not trigger merely because a task is non-trivial. |
| `using-agent-skills` | Need Addy Osmani lifecycle routing | Good general lifecycle map; this router adds Murphy-specific preferences. |
| `superpowers:using-superpowers` | Superpowers framework is explicitly requested or already active | It is stricter than normal Codex routing. |
| skill-install route | Installing or updating Codex skills from GitHub / curated / HTTPS / archive sources | First inspect whether the source is a real Codex skill. Use an available installer skill/script only if present; after install/update, return to this router and sync the map automatically. |
| plugin/connector route | Using or recommending plugins, apps, connectors, or MCP tools | Check callability first; use `tool_search` when needed; recommend/request install only under explicit install rules; apply cost/external side-effect gates. |
| `write-a-skill`, `create-expert-skill`, `superpowers:writing-skills` | Creating or editing skills | Prefer `superpowers:writing-skills` for discipline and validation; use `write-a-skill` for local skill edits; use `create-expert-skill` for production expert-knowledge skills. |
| `open-design-assistant` | Murphy wants Codex to open/use Open Design as a side visual canvas, convert design needs into prompts, review the current canvas, or edit saved Open Design artifacts | It is a local-canvas bridge, not a replacement for `frontend-design`. Use it when Open Design/localhost/.od shared files are part of the workflow. |
| `stepwise-agent-tutoring` | Murphy is learning Agent/RAG/hello-agent, wants one small teaching step, checkpoint/interview mode, note sinking, or repo-grounded progress | Teaching-first and source-aware; do not switch to implementation unless Murphy explicitly asks. |
| `hermes-control-gate-audit` | Murphy asks about Hermes board/control-plane progress, PAUSE, human gates, blocked cards, worker launch readiness, or why a Hermes workflow is not moving | Read-only audit route; do not dispatch, unblock, clear PAUSE, or edit repos unless explicitly authorized. |

## Requirements, Planning, And Product Thinking

| Skill | Choose It When | Avoid When |
|---|---|---|
| `quick-requirement-clarifier` | Existing repo/change request is fuzzy but close to implementable | New product/project with unclear goals. |
| `project-intake-interview` | Starting a product, website, technical project, or research effort from scratch | Tiny bugfix or already-scoped task. |
| `brainstorming` | Creative work or design/spec shaping before implementation, especially when the user wants collaborative exploration and approval gates | Do not use when Murphy asks to proceed directly with a small already-scoped implementation. Overlaps with `superpowers:brainstorming`; standalone copy installed at `~/.codex/skills/brainstorming` on 2026-05-22. |
| `interview-me` | Need one-question-at-a-time extraction of real intent | User asked to proceed directly. |
| `idea-refine` | Raw idea needs divergent/convergent exploration | Requirements already clear. |
| `grill-me` | Stress-test a plan/design outside codebase docs | Need repo glossary/ADR updates. |
| `grill-with-docs` | Stress-test design against project language, `CONTEXT.md`, ADRs | No repo/docs context exists. |
| `spec-driven-development` | New feature/significant change lacks a spec | One-line or obvious change. |
| `planning-and-task-breakdown`, `superpowers:writing-plans` | Clear requirements need ordered implementation tasks | Requirements still ambiguous. Use the Superpowers-prefixed name when choosing the Superpowers workflow. |
| `setup-matt-pocock-skills` | First-time per-repo Matt Pocock workflow setup: issue tracker, triage labels, and domain-doc layout | Skills are not installed globally; use skill-install route first. |
| `to-prd` | Turn current conversation/context into a PRD and publish it to the configured issue tracker | User wants a lightweight spec only and no issue-tracker artifact. |
| `to-issues` | Break a PRD/plan into tracer-bullet implementation issues with AFK/HITL classification | Requirements are still fuzzy enough to need `quick-requirement-clarifier` first. |
| `triage` | Review/create/move issues through `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix` | No issue tracker/config exists; run setup first. |

## Engineering Execution

| Skill | Choose It When | Overlap Notes |
|---|---|---|
| `incremental-implementation` | Multi-file implementation should proceed in thin slices | Pair with tests for behavior changes. |
| `test-driven-development` | Addy lifecycle test discipline for logic/bug/behavior changes | General and broad. |
| `tdd` | Matt Pocock red-green-refactor, integration-style tests, one tracer bullet at a time | Stronger guidance on test shape; good for serious feature/bug work. |
| `superpowers:test-driven-development` | Superpowers explicitly requested or strict TDD enforcement needed | More rigid; use when user wants discipline over speed. |
| `karpathy-guidelines` | Coding/review/refactor needs simplicity, assumptions, surgical scope | Lightweight behavioral guardrail; can support most coding tasks. |
| `source-driven-development` | Framework/library behavior may be version-sensitive or official docs matter | Must use official sources before implementing. |
| `api-and-interface-design` | Public API, module boundary, REST/GraphQL/type contract | Not for internal-only tiny helper changes. |
| `senior-backend` | Backend APIs, auth, DB, GraphQL, migrations, load tests | Backend-specific; pair with source docs for current frameworks. |
| `migrate-to-shoehorn` | TypeScript tests need `as` assertions replaced with `@total-typescript/shoehorn` | Niche test migration only. |
| `setup-pre-commit` | Add Husky/lint-staged/pre-commit checks | Requires repo package tooling. |

## Debugging, Review, And Quality

| Skill | Choose It When | Distinction |
|---|---|---|
| `diagnose` | Hard bug/perf regression needs reproduce -> hypothesis -> instrument -> fix | Strongest debugging loop; use for non-obvious bugs. |
| `debugging-and-error-recovery` | Test/build/runtime error needs systematic root-cause debugging | Broader Addy workflow. |
| `superpowers:systematic-debugging` | Superpowers is explicitly requested or already active during a debugging task | Similar to `diagnose`; pick one, not both. Default to `diagnose` for hard bugs. |
| `code-review-and-quality` | Review completed code/diff for correctness, readability, architecture, security, perf | Review stance, not implementation. |
| `superpowers:requesting-code-review` | Work is complete and needs review checkpoint | Superpowers completion review. |
| `superpowers:receiving-code-review` | User gives review feedback to address | Verify feedback before blindly applying. |
| `doubt-driven-development` | Non-trivial decision has high stakes or hidden assumptions | In-flight adversarial check, not final review. |
| `code-simplification` | Code works but is too complex | Preserve behavior; avoid feature work. |
| `improve-codebase-architecture` | Need structural refactor opportunities using domain docs/ADRs | Discovery/refactor planning, not a quick bugfix. |
| `zoom-out` | Need high-level explanation of unfamiliar code area | Explanation first, not change-first. |
| `performance-optimization` | Perf target/regression/Core Web Vitals/profiling | Measure before optimizing. |
| `security-and-hardening` | User input, auth, sessions, file upload, external APIs, PII, payments | Use as constraint on implementation/review. |

## Frontend, Browser, Figma, And Design

| Skill | Choose It When | Distinction |
|---|---|---|
| `frontend-design` | User cares about visual polish, layout, branded surface, marketing/site/dashboard feel | Design-quality lead. |
| `frontend-ui-engineering` | Building/modifying UI components, state, responsive behavior, accessibility | Implementation-quality lead. |
| `figma`, `figma-implement-design` | Figma URL/node/design-to-code fidelity is source of truth | Requires Figma MCP/tool access. |
| `browser-testing-with-devtools` | Need live DOM/console/network/perf data via Chrome DevTools MCP | Use if configured. |
| `playwright` | Need browser automation from terminal, screenshots, flows, scraping | Use when Browser/DevTools plugin unavailable or scripted checks are better. |
| `screenshot` | Need OS-level screenshot | Not for normal web verification. |
| `prototype` | Need throwaway UI variants or state-machine proof before committing | Exploratory, not production implementation. |

## Documents, Slides, PDFs, And Deliverables

| Skill | Choose It When | Distinction |
|---|---|---|
| `kami` | Need a polished PDF, one-pager, long doc, letter, portfolio, resume, slides PDF, equity report, changelog, or product landing page | Best for finished visual deliverables. Not primarily `.pptx` editing. |
| `pptx`, `pptx-skill` | Any `.pptx` must be created/read/edited, especially editable decks | If final output must be PowerPoint, use these instead of Kami. |
| `docx`, `doc` | Professional `.docx` creation/editing/extraction with formatting | Use for Word files; Kami is for styled HTML/PDF deliverables. |
| `pdf` | Reading/creating/reviewing PDF with layout/rendering checks | Use when existing or final artifact is PDF-specific. |
| `xlsx` | Spreadsheet files, formulas, charts, analysis | Not for generic tables in documents. |
| `assignment-support-coach` | Academic assignment planning/review from prompt/rubric | Does not write full assignment for user. |
| `edit-article`, `khazix-writer`, `baoyu-article-illustrator` | Article editing/writing/illustration | `edit-article` tightens prose; `khazix-writer` is a Chinese long-form persona; `baoyu-article-illustrator` adds image strategy. |

## Knowledge, Notes, Wiki, And Obsidian

| Skill | Choose It When | Distinction |
|---|---|---|
| `obsidian-markdown` | Create/edit Obsidian `.md` syntax: wikilinks, callouts, properties, embeds | File-format skill; no live app required. |
| `obsidian-bases` | Create/edit `.base` database views, filters, formulas | Obsidian Bases only. |
| `json-canvas` | Create/edit `.canvas` visual maps | JSON Canvas only. |
| `obsidian-cli` | Live vault operations via `obsidian` CLI | Requires Obsidian open and CLI installed. |
| `obsidian-vault` | Older personal vault workflow | Verify path first; may contain stale author-specific path. |
| `wiki-query`, `wiki-explain-page`, `wiki-ingest`, `wiki-lint` | Local-first WiKi repo tasks at `<WIKI_REPO_PATH>` | Use these for the WiKi project, not Obsidian skills. |
| `start-my-day` | Daily arXiv paper recommendations into Obsidian, including top-paper detail passes | Requires `OBSIDIAN_VAULT_PATH`, `99_System/Config/research_interests.yaml`, Python deps, and network. Writes `10_Daily/` notes. |
| `paper-analyze` | Deep analysis of one arXiv paper/title into a structured Obsidian paper note | Use instead of generic summary when Murphy wants durable paper notes and images. May call `extract-paper-images`. |
| `paper-search` | Search existing Obsidian paper notes by title, author, keyword, field, or tag | Existing-note search only; not live arXiv/web search. |
| `conf-papers` | Top-conference paper recommendation from CVPR/ICCV/ECCV/ICLR/AAAI/NeurIPS/ICML | Uses DBLP + Semantic Scholar; choose over `start-my-day` when the cue is conference/year-specific. |
| `extract-paper-images` | Extract paper figures from arXiv source/PDF into paper-note image folders | Auxiliary image route; not an image-generation skill. |
| `defuddle` | Clean webpage -> Markdown via Defuddle CLI | Requires `defuddle`; use web browsing if not installed. |
| `neat-freak` | End-of-session knowledge/documentation alignment | Not disk cleanup. |
| `handoff` | Compact current conversation for another agent | Use for continuity, not final report. |

## Research, News, And External Sources

| Skill | Choose It When | Notes |
|---|---|---|
| `aihot` | Chinese AI news/daily/hot items | Uses public API; do not answer AI news from memory. |
| `market-landscape-researcher` | Competitor/product landscape research with links | Browse current sources. |
| `openai-docs` | OpenAI API/product/docs question | Use official docs/MCP; restrict fallback browsing to OpenAI domains. |
| `codex-usage-auditor` | Token/credit/API-equivalent cost or subscription value | Local usage audit. |
| `fyp-repo-audit` | X2-DFD final-year project audit | Very project-specific. |
| `wechat-miniapp-preflight-review` | WeChat miniapp release QA | Project/release specific. |
| `weread-skills` | WeChat Reading search, notes, bookshelf, reviews | Requires corresponding API/tool assumptions. |
| `yao-weread-skill` | WeChat Reading history analysis, reading report, stats charts, reader portrait, or polished HTML report | Use for “近几年读书历史/兴趣类别/生成报告/可视化/HTML”. It depends on `weread-skills` config and `WEREAD_API_KEY`; choose `weread-skills` instead for raw lookup/search/book notes without a report. Restart Codex after install if it is not visible. |

## Media And Generation

| Skill | Choose It When | Distinction |
|---|---|---|
| `imagegen` | OpenAI Image API generation/editing, generate image, create image, draw image, image edit | Requires `OPENAI_API_KEY`; direct image work. |
| `baoyu-image-gen` | Multi-provider image generation or batch prompts, 文章配图, 生成配图, 科技感, 海报风格控制 | Good for provider choice/batch throughput. |
| `image2-prompt-guide` | Need prompt engineering for GPT-Image2/image-to-image | Prompt crafting, not necessarily generation. |
| `sora` | OpenAI video generation/remix/download | Requires Sora API access. |
| `speech` | Text-to-speech/voiceover/audio prompt | Requires OpenAI Audio API. |
| `transcribe` | Audio/video transcription and speaker labels | Use for recordings. |
| `hatch-pet` | Codex animated pet spritesheet/package | Specialized asset pipeline. |

## Deployment, Git, Automation, And Platforms

| Skill | Choose It When | Distinction |
|---|---|---|
| `git-workflow-and-versioning` | Commits, branches, conflicts, atomic history | Pair with implementation completion. |
| `superpowers:finishing-a-development-branch` | Work done, decide merge/PR/cleanup | Superpowers completion path. |
| `superpowers:using-git-worktrees` | Need isolated feature worktree | Use before risky feature branches. |
| `ci-cd-and-automation` | Pipelines, quality gates, deploy automation | CI/CD focus. |
| `shipping-and-launch` | Production rollout, monitoring, rollback | Launch readiness. |
| `vercel-deploy` | Deploy app/site to Vercel, preview URL | Vercel deployment only. |
| `deprecation-and-migration` | Remove old systems or migrate users/APIs | Sunset/migration planning. |
| `git-guardrails-claude-code` | Claude Code git safety hooks | Claude-specific; not general Codex git safety. |

## Skill Authoring And Tooling

| Skill | Choose It When | Distinction |
|---|---|---|
| `mcp-builder` | Build MCP server integrations | Tool-channel work, not static skills. |
| `notion-spec-to-implementation` | Turn Notion specs into implementation plans/tasks | Requires Notion context/tools. |
| `create-expert-skill` | Convert expert knowledge into production skill | Higher rigor than quick local skill. |
| `superpowers:writing-skills` | Edit/create skills with validation discipline; 改这个 skill, 加 eval case, 验证 skill, router 迭代 | Use for this router and reusable skills. |

## Hold / Not A Codex Skill

| Repo/Tool | Status | Why It Matters |
|---|---|---|
| `multica-ai/multica` | Not installed; local clone deleted | Managed-agent platform, not a skill pack. Useful later for assigning issues to agents, not for router auto-trigger. |
| `ruvnet/ruflo` | Not installed | Heavy agent/swarm/MCP orchestration layer, mostly Claude/Codex CLI setup, not a lightweight skill. |

## Recently Added Skill Packs

| Source | Installed Skills | Router Note |
|---|---|---|
| `mattpocock/skills` | `setup-matt-pocock-skills`, `to-prd`, `to-issues`, `triage`, `tdd`, `diagnose`, `improve-codebase-architecture`, `zoom-out`, `grill-me`, `grill-with-docs`, `prototype`, `handoff`, `setup-pre-commit`, `migrate-to-shoehorn`, `scaffold-exercises`, `write-a-skill`, `git-guardrails-claude-code`, `caveman`, plus misc/personal helpers | Strong engineering workflow pack. Prefer Matt skills for repo/domain-doc workflows, PRD-to-issue flow, disciplined debugging/TDD, and design interrogation. Run `setup-matt-pocock-skills` per repo before PRD/issue/triage workflows if `docs/agents/*` is missing. |
| `addyosmani/agent-skills` | lifecycle skills from `using-agent-skills` through spec/plan/build/test/review/ship | Strong end-to-end quality gate pack. Prefer for broad lifecycle and production discipline. |
| `kepano/obsidian-skills` | `obsidian-markdown`, `obsidian-bases`, `json-canvas`, `obsidian-cli`, `defuddle` | Obsidian file formats and vault operations. Verify CLI availability for live app operations. |
| `tw93/kami` | `kami` | Polished deliverables and document design system. Needs rendering dependencies for PDF/PPTX workflows. |
| `yaojingang/yao-open-skills` | `yao-weread-skill` | Generates private WeRead visual reports from the local WeRead API key. Route natural asks like “分析我的微信读书历史”, “近三年读书报告”, “看我感兴趣的书目类别”, and “生成微信读书 HTML 报告” here. |
| `juliye2025/evil-read-arxiv` | `start-my-day`, `paper-analyze`, `extract-paper-images`, `paper-search`, `conf-papers` | Installed 2026-05-28 as a Claude/Codex paper-reading skill pack. Route natural asks like “start my day”, “每日 arXiv 论文推荐”, “分析这篇论文”, “提取论文图片”, “搜已有论文笔记”, and “顶会论文推荐” here. Requires Codex restart/inventory refresh before automatic trigger in new sessions, plus `OBSIDIAN_VAULT_PATH` and `research_interests.yaml` before live use. |
| local Codex skill | `open-design-assistant` | Opens and coordinates Murphy's local Open Design canvas. Route natural asks like “打开 Open Design”, “进入设计模式”, “用 Open Design 画布”, “读取/修改当前设计稿”, or “localhost:64392” here; it uses `.od/projects` and `.od/artifacts` as the shared file bridge. |
| local Codex skills | `stepwise-agent-tutoring`, `hermes-control-gate-audit` | Added 2026-05-25 from recent workflow packaging audit. Use `stepwise-agent-tutoring` for Agent/RAG learning loops and `hermes-control-gate-audit` for Hermes read-only gate/progress audits. Restart or refresh skill inventory if they are not visible in a new session. |
| local Codex resume/interview skills | `resume-optimizer`, `resume-backend-project-optimizer`, `resume-interview-coach`, `interview-officer`, `resume-template-from-image` | Added before 2026-06-06 sync; `interview-officer` added 2026-06-23. Route resume audit/rewrites, backend project bullet sharpening, interview defense, strict simulated interview, and image-based resume-template generation to these skills based on output surface and project context. |
| local Codex internship/trading skills | `shushu-internship-tool`, `futuapi`, `install-futu-opend` | Added before 2026-06-06 sync. Route internship JD-to-project prep to `shushu-internship-tool`; route Futu market/account/API actions to `futuapi`; route OpenD install/config to `install-futu-opend`. |
| workspace Codex skill via RedSkill | `lishu-serenity` / `serenity-supply-chain-thesis` | Installed under `<LISHU_SERENITY_SKILL_PATH>`. Route Serenity-style AI infrastructure, photonics/CPO, semiconductor, neocloud, and supply-chain chokepoint thesis writing here; use current-source checks and investment-risk caveats. |
| enabled plugin set | Public Equity Investing, Investment Banking, Data Analytics, Spreadsheets, Documents, Presentations, Product Design, Creative Production | Added 2026-06-06 as explicit plugin records. Use plugin preflight/tool_search callability checks before claiming execution; recommend Public Equity Investing first for stock research, Data Analytics/Spreadsheets for portfolio data, Investment Banking for deal/valuation workflows, Product Design/Creative Production for prototype/creative exploration, and Documents/Presentations for artifact creation. |
| CodeHarness-Lite project skills | `repo-context`, `feature-implementation`, `bugfix-repair`, `test-generation`, `pr-review` under `<CODEHARNESS_SKILLS_PATH>` | Added 2026-06-08 for RepoPilot Harness. Route CodeHarness-Lite / RepoPilot asks about context packs, project context refresh, scoped feature work, bug repair, test generation, and PR review to these project-local skills first; refresh skill inventory or open the local `SKILL.md` directly if they are not visible globally. |
