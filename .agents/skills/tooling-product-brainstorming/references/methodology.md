# Brainstorming methodology (reference)

Loaded on demand from `tooling-product-brainstorming/SKILL.md`. Holds the seven frameworks, the five-phase session structure, and the anti-pattern catalog. Read this file when you need a specific framework or want to walk a full session shape; the SKILL.md is the lightweight router that points here.

Source: anthropics/knowledge-work-plugins product-management/skills/product-brainstorming.

## Brainstorming Frameworks

Use frameworks as thinking tools, not templates to fill in. Pull in a framework when it helps move the conversation forward. Do not force every conversation through every framework.

### How Might We (HMW)

Reframe problems as opportunities. Turn a pain point into an actionable question.

**Structure**: "How might we [desired outcome] for [user] without [constraint]?"

**Tips:**
- Too broad: "How might we improve onboarding?"  -  could mean anything
- Too narrow: "How might we add a tooltip to step 3?"  -  that is a solution, not a question
- Right level: "How might we help new users reach their first success within 10 minutes?"
- Generate 5-10 HMW questions from a single problem statement. Each reframing opens different solution spaces.

### Jobs-to-be-Done (JTBD)

Think from the user's job, not from features or demographics.

**Structure**: "When [situation], I want to [motivation] so I can [expected outcome]."

**Tips:**
- The job is stable even when solutions change. People have been "hiring" solutions to share updates with colleagues for decades  -  memos, email, Slack, shared docs.
- Functional jobs (get something done) are easier to identify. Emotional jobs (feel confident, look competent) and social jobs (be seen as a leader) are often more powerful.
- Ask "What did they fire to hire your product?"  -  this reveals the real competitive set.

### Opportunity Solution Trees

Map the path from outcome to experiment.

```
Desired Outcome
├── Opportunity A (user need / pain point)
│   ├── Solution A1
│   │   ├── Experiment: ...
│   │   └── Experiment: ...
│   └── Solution A2
│       └── Experiment: ...
├── Opportunity B
│   ├── Solution B1
│   └── Solution B2
└── Opportunity C
    └── Solution C1
```

**Tips:**
- Opportunities come from research, not imagination. Every opportunity should trace back to evidence.
- Multiple solutions per opportunity. If you only have one solution, you have not explored enough.
- Multiple experiments per solution. Find the cheapest way to test before building.
- The tree is a living artifact. Update it as you learn.

### First Principles Decomposition

Break a complex problem down to its fundamental truths and rebuild.

1. **State the problem or assumption** you want to examine
2. **Break it down**: What are the fundamental components or constraints?
3. **Question each component**: Why does this have to be this way? Is this a law of physics or a convention?
4. **Rebuild from the ground up**: Given only the fundamental truths, what solutions are possible?

**When to use**: When the team is stuck in incremental thinking. When everyone says "that is just how it works." When the category has not been reimagined in years.

### SCAMPER

Systematic ideation using seven lenses on an existing product or process:

- **Substitute**: What component could be replaced? What if a different user did this step?
- **Combine**: What if we merged two features? Two workflows? Two user roles?
- **Adapt**: What idea from another product or industry could we borrow?
- **Modify**: What if we made this 10x bigger? 10x smaller? 10x faster?
- **Put to other use**: Could this feature serve a different user or use case?
- **Eliminate**: What if we removed this entirely? Would anyone notice?
- **Reverse**: What if we did the opposite? Flipped the sequence? Inverted the default?

### OODA Loop (Observe / Orient / Decide / Act)

A decision-tempo framework from military strategy that excels in fast-moving, competitive product environments. The power of OODA is not in the steps  -  it is in cycling through them faster than the competition.

1. **Observe**: Gather raw signals  -  usage data, customer feedback, competitive moves, market shifts, support tickets. Do not filter yet. Cast wide.
2. **Orient**: Make sense of what you observed. This is the critical step. Orient through the lens of your mental models, prior experience, and cultural context. Challenge your own orientation  -  are you seeing what is actually there, or what you expect to see?
3. **Decide**: Choose a direction. Not a final commitment  -  a hypothesis to test. The decision should be proportional to what you know. Small bets when uncertain, bigger moves when the signal is clear.
4. **Act**: Execute the decision. Ship something. Run the experiment. Make the change. Then immediately return to Observe with new data.

**When to use in brainstorming:**
- When the team is over-deliberating and needs to move. OODA favors tempo over perfection.
- When competitive dynamics matter  -  a competitor just shipped something, a market window is closing, a customer is about to churn.
- When the brainstorm keeps circling without converging. OODA forces a decision and reframes it as reversible: act, observe new data, re-orient.
- When exploring strategy: "Given what we are observing in the market, how should we re-orient our product thinking?"

**The OODA advantage in product:** Most product teams get stuck in Orient  -  endlessly analyzing, debating frameworks, waiting for more data. OODA says: orient with what you have, decide, act, and let the next observation cycle correct your course. The team that cycles fastest learns fastest.

### Reverse Brainstorming

When stuck on how to solve a problem, brainstorm how to make it worse.

1. **Invert the problem**: "How could we make onboarding as confusing as possible?"
2. **Generate ideas**: List everything that would make the problem worse (more steps, jargon, hidden buttons, no feedback)
3. **Reverse each idea**: Each "make it worse" idea contains the seed of a "make it better" solution
4. **Evaluate**: Which reversed ideas are most promising?

**Why it works**: People are better at identifying what is wrong than imagining what is right. Inversion unlocks creative thinking when the team is stuck.

## Session Structure

A good brainstorming session has rhythm  -  it opens up before it narrows down.

### 1. Frame

Set boundaries before generating ideas. Good framing prevents wasted divergence.

- What are we exploring? (A specific problem, an opportunity area, a strategic question)
- Why now? (What triggered this brainstorm?)
- What do we already know? (Prior research, data, customer feedback)
- What are the constraints? (Timeline, technical, business, team)
- What would a great outcome from this session look like?

Spend enough time framing. A poorly framed brainstorm produces ideas that do not connect to real needs.

### 2. Diverge

Generate many ideas. No judgment. Quantity enables quality.

- Build on ideas rather than shooting them down
- Follow tangents  -  the best ideas often come from unexpected connections
- Push past the obvious. The first 3-5 ideas are usually the ones everyone would have thought of. Keep going.
- Ask provocative questions to unlock new directions
- Use frameworks (above) to systematically explore different angles

### 3. Provoke

Challenge and extend thinking. This is where the sparring partner role matters most.

- "What is the strongest argument against this?"
- "Who would hate this and why?"
- "What are we not seeing?"
- "What would [specific company or person] do differently?"
- "What if the opposite were true?"
- "What is the version of this that is 10x more ambitious?"

### 4. Converge

Narrow down. Evaluate ideas against what matters.

- Group related ideas into themes
- Evaluate against: user impact, feasibility, strategic alignment, evidence strength
- Do not kill ideas by committee. If one idea excites the PM, explore it  -  even if it is risky. The brainstorm is not the decision.
- Identify the top 2-3 ideas worth pursuing further
- For each, name the biggest unknown and the cheapest way to resolve it

### 5. Capture

Document what matters. A brainstorm with no capture is a brainstorm that never happened.

- Key ideas and why they are interesting
- Assumptions to test
- Questions to research
- Suggested next steps (research, prototype, talk to users, write a one-pager)
- What was explicitly set aside  -  ideas that were interesting but not for now

## Common Brainstorming Anti-Patterns

**Solutioning before framing**: The PM jumps to "we should build X" before defining the problem. Slow them down. Ask what user problem X solves and how we know.

**The feature parity trap**: "Competitor has X, so we need X." This is not brainstorming  -  it is copying. Ask what user need X serves and whether there is a better way to serve it.

**Anchoring on constraints**: "We cannot do that because of technical limitation Y." In divergent mode, set constraints aside. Explore freely first, then figure out feasibility.

**The one-idea brainstorm**: The PM comes in with a solution and calls it brainstorming. Acknowledge their idea, then push for alternatives. "That is one approach. What are three others?"

**Analysis paralysis**: Too much exploration, no convergence. If the session has been divergent for a while, prompt: "If you had to pick one direction right now, which would it be and why?"

**Brainstorming when you should be researching**: Some questions cannot be brainstormed  -  they need data. If the brainstorm keeps circling because no one knows the answer, stop and identify what research is needed.
