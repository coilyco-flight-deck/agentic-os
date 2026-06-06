# Rule: top and bottom never collapse into one

Intro and Outro look like two styles of one block. They are not. They are two times.

**Why:** the entire advantage of moving docs into the CLI instead of a skill is that the CLI controls **when** text enters the agent's context. A skill blob enters once, at trigger. A CLI injects at start, during, and at completion. The agent's context at completion is not its context at start - it has done the work, the window has churned. Outro content like "now end the session" is only knowable at the bottom (it depends on how the run went) and only actionable at the bottom. Front-load it and the agent reads it, works for 40 minutes, and the nudge is stale or evicted before it is relevant. Bottom-emission is recency placement: the next action goes where the agent reads it last, so it is freshest when it is needed.

**How to apply:** never answer "can all the info live at the top" with yes. The five tiers have a hard floor of distinct pre-run and post-run surfaces. Collapsing them throws away the only reason to leave a skill markdown behind.
