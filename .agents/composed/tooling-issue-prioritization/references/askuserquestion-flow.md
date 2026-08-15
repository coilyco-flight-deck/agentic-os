# AskUserQuestion flow

Where human judgment actually enters. Tiering orders a backlog and the [autonomy axis](automation-mode-axis.md) names each issue's ceiling. Neither drains `autonomy/async-consult`, and that queue is the one blocking real work. This is the loop that does.

`async-consult` is defined as a question waiting in a queue rather than an appointment. **A queue nobody polls is just a label.** These rounds are the polling.

## The loop

1. **Read first.** Open the issue body **and its comments** before composing anything. Detail migrates into threads, so the body alone is a description of the ticket rather than the ticket. A question the issue already answers spends a round you do not get back.
2. **Cluster, then batch.** Group issues sharing a decision and ask up to four questions per round, so related calls are made against each other rather than in isolation.
3. **Ask per decision, not per issue.** Two issues blocked on the same call take one question. One issue with three open unknowns takes three.
4. **Record before the next round.** Write the answer into the tracker - the body when it is a spec, a comment when the thread is long. Name what was chosen, what was rejected, and why.
5. **Relabel.** An issue whose blocking decision has landed is no longer `autonomy/async-consult`. Move it to `autonomy/headless` or `autonomy/live-collab` and say which condition was discharged.

`role/*` tells you whose queue an issue sits in, so ask the seat that owns it rather than whoever is in front of you.

## Writing the options

- **Every option is a branch a reasonable person might take**, with its cost stated. A set with one obviously-right answer is theatre and burns the round.
- **Recommended option first**, marked as such, when there is one.
- **Name the trade, not the label.** "Cache until restart - cheapest, and a rules edit needs a restart to take effect" beats "cache".
- **Carry the measurements into the option text.** Someone choosing a timeout wants the observed p95 in front of them, not in another tab.
- **Multi-select only when the choices compose.** Mutually exclusive options behind a multi-select produce answers that cannot all hold.

## What to record

- The decision, in words that bind a builder.
- **Every rejected alternative, with its reason.** This is what stops the question being re-asked next month, and it is the half most often dropped.
- The acceptance criteria the decision implies.
- Whatever is still unresolved, with its owner. A round answering three of four is a good round.

## Failure modes

- **Asking what the issue answers.** Read the comments.
- **A question that is not really multiple choice.** Some issues need a design pass rather than a picker. Say so, write a decision register naming each unknown and its owner, and do not force a choice.
- **An ambiguous answer.** A multi-select returning contradictory options is not licence to guess. Record the conservative reading, flag it in the same comment, and confirm next round.
- **Losing the answer.** An answer living only in chat is gone. Write it to the tracker in the same turn it arrives.
- **Cross-ticket contradictions.** A sweep surfaces decisions that conflict across issues, usually because each was made alone. Those earn a question of their own, and the answer supersedes one of the two.
- **Silent scope drift.** When an answer reverses an earlier decision, amend the issue that carried it. An unamended superseded spec is worse than none.
