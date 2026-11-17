---
name: start
description: >-
  Single entry point for this skill collection: reads the request, loads the first skill that
  fits, follows its workflow, then decides the next skill from what that step produced, up to
  four hops, and prints the route it took. Use when the user does not know which skill to use,
  wants one command for everything, or says "where do I start", "go handle it", "which skill",
  "ไปไหนต่อ", "เริ่มจากไหน", "เรียกสกิลเดียว", "จัดการต่อเอง". Triggers include "@start",
  "start", "single entry", "route this", "one skill", "เริ่มจากไหน", "ไปไหนต่อ". Not for a
  request that already names a skill - load that skill directly.
license: MIT
metadata:
  version: "1.0.0"
  tags: "router, entry-point, orchestration"
  category: "meta"
  tier: "core"
allowed-tools: Read Glob Grep Skill Subagent
---

# Start - one entry, then chain

The user types one request. The agent picks the first skill, runs it, then looks at what came
out and decides the next hop. No menu, no "which skill would you like", no plan made before
the first step.

## When to use

- The user does not know which skill applies.
- The work will obviously need more than one skill.
- The user says "manage it", "go do it", or asks where to start.

## When not to use

- The request already names a skill (`@grill-ai`, "use z3") - load it directly.
- One skill obviously covers the whole request - load that one.
- The request is a single question with no artifact - answer it.

## Rules

1. **Route, do not re-implement.** If a skill covers the next step, load it with the `skill`
   tool and follow it. The router adds no domain knowledge of its own.
2. **One hop at a time.** Decide the next skill from the deliverable the last one produced,
   not from a plan written at the start.
3. **Cap the chain at four skills.** Stop when a deliverable exists, when the next hop would
   repeat the previous one, or when two hops produced no new artifact.
4. **Announce the route.** First line: `route: start -> <id>`. Update it when the route
   changes. One line, no commentary.
5. **Never ask which skill.** Pick. Ask the user only a question that a loaded skill requires.
6. **No match means no skill.** Do the work directly and print `route: none`.
7. **Explicit beats inferred.** A skill the user names wins over the table.
8. **Do not hide the collection.** This router is an entry, not a gate: never set
   `opencode/autoinvoke: false` on the other skills to force traffic through here.

## Route table

| Request shape | First | Then |
|---|---|---|
| unfamiliar repo, "where do I start", onboarding | project-onboarding | aiwor |
| vague request, unclear scope, keeps changing | aiwor | decompose |
| clear goal, large or multi-step work | decompose | - |
| question needing research, a recommendation or a decision | grill-ai | reality-check |
| package, version, API, flag, config key or URL fact | reality-check | - |
| UI, design system, themes, accessibility, contrast | design-review | - |
| constraint, scheduling or satisfiability puzzle | z3-solver | - |
| birth chart, ดูดวง, Bazi, ลัคนา, Human Design | divination-charts | - |
| name analysis, เลขศาสตร์ชื่อ, ตั้งชื่อ | thai-name-numerology | - |
| create, lint or repair a skill | skill-creator | grill-ai |

The `Then` column is a default, not an order. Take it only when its gate below is true.

## Gates between hops

| Handoff | Take it only when |
|---|---|
| project-onboarding -> aiwor | `BOOK.md` exists and the request is still ambiguous |
| aiwor -> decompose | the plan has more than three steps or parallel branches |
| decompose -> implementation | the task graph has acceptance criteria and a verify command per task |
| grill-ai -> reality-check | a load-bearing package, version or API claim is still unverified |
| skill-creator -> grill-ai | the new skill makes a factual claim that must survive review |

Stop at the first row that no longer applies.

## Handoff

After each skill, write one line of state before choosing the next hop:

```
state: <artifact produced> | next: <id or none> | why: <six words>
```

Read the artifact. If it already satisfies the request, stop - a second skill that adds no
artifact is a wasted hop. If a skill's own `SKILL.md` names its successor, that wins.

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| Four skills loaded, nothing produced | router doing the work instead of routing | return to the table; load one skill, finish it |
| The user is asked to choose a skill | router turned into a menu | decide from the request shape |
| Endless chain | no stop condition | deliverable test: can the user act on it now? |
| Wrong first skill | guessed from topic, not from artifact | look for a repo, a file, a number, a decision |
| Router silently overrides `@skill` | explicit request ignored | rule 7 |
| Table rots after a rename | ids copied by hand | run `scripts/check_routes.py` |

## Files

- `scripts/check_routes.py` - verifies every id in the route table resolves to a real skill
  directory; run it after adding, renaming or deleting a skill.
- `scripts/selftest.py` - regression tests for the route check.
