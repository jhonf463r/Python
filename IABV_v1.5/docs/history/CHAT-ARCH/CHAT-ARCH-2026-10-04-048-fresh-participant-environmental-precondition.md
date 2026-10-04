# CHAT-ARCH-2026-10-04-048 — FRESH-PARTICIPANT ENVIRONMENTAL PRECONDITION

## PURPOSE

Reconcile repeated fresh-participant ineligibility with the documented Claude session context mechanisms.

## OBSERVED

Multiple attempted participant sessions returned:
`INELIGIBLE — PRIOR CONTEXT PRESENT`

The failures occurred despite opening what was intended to be a new conversation.

## EXTERNAL PLATFORM FACT

Anthropic documents that Claude can search and reference previous conversations in new chats when the feature is enabled. Anthropic also documents that Profile Preferences are account-wide and that Project knowledge/instructions apply to chats within the project.

Therefore:

`new chat != guaranteed context isolation`

A fresh participant run requires environmental isolation in addition to a new conversation.

## CURRENT EXPERIMENTAL PRECONDITION

Before running the participant:

1. Disable Claude's setting `Search and reference chats` in Settings → Profile → Preferences, where available.
2. Do not execute the participant inside an IABV project workspace containing project knowledge or project instructions.
3. Start a new conversation after the setting/state is isolated.
4. Attach only the frozen participant ZIP.
5. Send only the participant TASK/prompt.
6. Do not provide earlier experiment text or project context.

## EPISTEMIC LIMIT

The experiment cannot prove that all hidden model/account context is absent.

It can establish only that the operator configured the documented conversation/project context controls and supplied no external project material.

If the participant still reports prior project/task context, mark the run:
`INELIGIBLE — PRIOR CONTEXT PRESENT`

## ROUTING

Current participant remains:

`SONNET / CLAUDE — FRESH PARTICIPANT`

This is an environmental precondition for the participant, not a change of actor.

Next after two eligible outputs:
`CODEX DISTINCT — INDEPENDENT ADJUDICATOR`

## CURRENT FRONTIER

`consolidated canonical memory availability → reproducible fresh-chat activation into the current decision frame`

## METHOD DELTA

`fresh conversation` must now mean:

`new conversation + past-chat reference disabled + outside project workspace + no prior project/task material in the conversation`

## STOP

Do not score any participant until the precondition is satisfied and the participant does not disclose prior project/task context.
