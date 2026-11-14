# Writing descriptions that trigger

The description is the only thing the agent sees before it decides to load the skill.
A perfect body behind a vague description never runs.

## Formula

```
<What it does, in concrete verbs and nouns>.
Use when <task shape>, <task shape>, or <signal the user gives>.
Triggers include "<phrase>", "<phrase>", "<Thai phrase>".
```

Rules of thumb:

1. **Lead with the outcome**, not the domain. "Splits work into verifiable tasks" beats
   "project management helper".
2. **Name the artifacts.** `SKILL.md`, `tasks.json`, `PDF forms`, `docker-compose.yml`.
   Users and agents search by noun.
3. **Describe the request, not the skill.** Match how a user would phrase the ask.
4. **Include near-synonyms and the user's language.** Thai users often type
   "แยกงาน", "แตกงาน", "วางแผนงาน" while the body is in English.
5. **State the boundary.** "Use when X, not when Y" reduces false activations.
6. **Stay under 1024 characters.** Aim for 200-500; long descriptions dilute keywords.

## Good

```yaml
description: >-
  Decomposes vague or oversized work into atomic, verifiable tasks with a
  dependency DAG, critical path and risk spikes. Use when the user asks to break
  down a project, plan a refactor or migration, scope an epic, build a WBS,
  backlog or sprint plan, or says a task is too big, blocked or unclear.
  Triggers include "decompose", "break this down", "WBS", "แยกงาน", "แตกงาน".
```

Why it works: verbs (`decompose`, `plan`, `scope`), nouns (`WBS`, `backlog`, `DAG`), the
request shape ("a task is too big"), and multilingual triggers.

## Bad

```yaml
description: Helps with project planning and tasks.
```

Fails because it has no artifact, no request shape, no trigger words, and would match
almost any planning conversation.

## Optimizing after the fact

1. Collect 10 real prompts that should activate the skill and 5 that must not.
2. For each, ask: would a keyword match fire? Which words are missing?
3. Add the missing nouns to the description, then re-read it as a single sentence.
4. Remove words that also appear in common unrelated requests ("help", "code", "write").

## Multilingual checklist

- Keep the body in one language, usually English for token efficiency.
- Put trigger phrases in every language the user actually types.
- Never translate tool names, file names or commands.
