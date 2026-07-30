# Agent SDK patterns

Compact reference map for reusable agent-design patterns. These patterns are implementation options, not defaults. Apply the repository's role, authority, privacy, and validation rules before adopting one.

## Coordination and context

* **Specialist teams** - give subagents differentiated tools and scoped responsibilities, then make one coordinator synthesize their work.
* **Chief-of-staff orchestration** - use a top-level agent, subagents, hooks, and output styles when a task needs several specialist passes.
* **Context engineering** - choose deliberately between durable storage, in-conversation compaction, and tool-result clearing.
* **Manual and automatic compaction** - compact long-running sessions explicitly when the transition needs judgment, or automatically when uninterrupted work matters more.
* **User memory** - distinguish cross-session user preferences from durable repository doctrine and current task state.
* **Session browsers** - treat recorded sessions as a searchable audit source rather than rebuilding a transcript parser.
* **Self-verification** - use a stateless second pass to grade a result when grading costs less than producing it.

## Operations and security

* **Read-only observability** - connect agents to monitoring and CI evidence without granting mutation authority.
* **Incident response** - separate diagnosis, remediation, pull-request creation, and human approval into explicit gates.
* **Vulnerability investigation** - threat-model the target, collect evidence, and report findings structurally before proposing remediation.
* **Threat-intelligence enrichment** - fan out across several bounded read sources, then reconcile results into one report.

## Tools and execution

* **Tool search** - retrieve a small relevant subset of a large tool catalog rather than eagerly loading every definition.
* **Programmatic tool calling** - use a sandboxed program to orchestrate many dependent calls when it materially reduces latency and token cost.
* **Small research agents** - start with a narrow web-research loop before introducing specialist orchestration.

## Managed-agent delivery

* **Production setup** - model credentials, environment lifecycle, idled sessions, and human handoff as first-class concerns.
* **Prompt versioning** - evaluate labeled changes and retain a rollback path for deployed prompts.
* **Data analysis** - use sandboxed file mounts and constrained output formats for structured-data analysis.
* **Chat-surface analysis** - preserve session context across follow-ups while keeping channel authority bounded.
* **Failing-test iteration** - use a small known-bug exercise to verify the basic agent, environment, session, and streaming loop.

## Quality and experience

* **Custom skills** - package recurring organizational workflows into narrow, discoverable instruction surfaces.
* **Tool evaluation** - test one tool definition against many representative tasks rather than inferring quality from a single run.
* **Speculative prompt caching** - warm likely prompt prefixes only when the latency benefit justifies the prediction risk.

## Related

[Skill discipline](skill-discipline.md), [context budget](context-budget.md), [agents and sessions](features-agents-sessions.md), and [test harnesses](test-harness.md).
