# Skill landscape (checked 2026-11-14)

Source: <https://skills.sh> - the public registry (Vercel) that indexes agent skills and
their install counts. Numbers below are from the leaderboard page today.

## How skills are distributed now

- Install is one command: `npx skills add <owner/repo> --skill <name>`.
- Clients listed: Claude Code, Cursor, Codex, Copilot, Windsurf, Gemini, Cline, AMP,
  OpenCode, VS Code, Zed and others.
- Registry shows install counts, GitHub stars, first-seen date and **security audits**
  (Agent Trust Hub, Socket, Snyk).
- Total leaderboard size: ~1.38M skills indexed.

## What is actually popular

| Rank | Skill | Installs | Category |
|---|---|---|---|
| 1 | `vercel-labs/skills/find-skills` | 4.4M | meta / discovery |
| 3 | `mattpocock/skills/grill-me` | 1.5M | review / questioning |
| 7 | `designed-by-ai/skills/design-mobile-apps` | 1.4M | design |
| 15 | `anthropics/skills/frontend-design` | 1.1M | design |
| 17 | `uizze.sh/ui-taste` | 1.1M | design taste |
| 62 | `vercel-labs/agent-skills/web-design-guidelines` | 860K | design rules |
| 75 | `leonxlnx/taste-skill/design-taste-frontend` | 774K | design taste |
| 177 | `nextlevelbuilder/ui-ux-pro-max` | 450K | design system |
| 196 | `anthropics/skills/skill-creator` | 431K | meta |
| 269 | `obra/superpowers/systematic-debugging` | 332K | debugging |
| 293 | `obra/superpowers/verification-before-completion` | 275K | verification |

## What the top UI/UX skills contain

`ui-ux-pro-max` (450K installs, 149K stars, first seen 2026-01-19) describes itself as:

- 79 searchable styles (50 active), 192 product palettes, 74 font pairings,
  119 UX guidelines, 105 icons, 25 chart types, 22 technology stacks.
- Rules ranked by priority 1-10; full text lives in a `quick-reference.md` inside that
  skill and is read **on demand** with `--domain <Domain>`.
- Covers React, Next.js, Vue, **Svelte**, SwiftUI, React Native, Flutter, Tailwind,
  shadcn/ui, HTML/CSS.
- Ships a searchable local database plus templates for landing pages, dashboards,
  admin panels, e-commerce, SaaS, portfolios, blogs and mobile apps.

Pattern to copy: **data in references, loaded only when queried** - not a 5,000-line
SKILL.md.

## Four skill archetypes that dominate

1. **Discovery / meta** - `find-skills` tells the agent which skill to load next.
   Highest installs of all, which says the bottleneck is knowing what exists.
2. **Taste packs** - `taste-skill/*`, `ui-taste`, `frontend-design`: opinionated
   visual direction, anti-default critique, "make it not look generated".
3. **Platform rules** - `web-design-guidelines`, `apple-design`, `ios-design`,
   per-framework best practices (Vercel React, Remotion, Prisma, Supabase).
4. **Process guards** - `verification-before-completion`, `systematic-debugging`,
   `test-driven-development`, `writing-plans`: force a check before declaring done.

## Where our repository sits

We already cover: planning (`decompose`), verification (`reality-check`),
authoring (`skill-creator`), design (`design-review`).

Gaps suggested by the leaderboard:

| Gap | Why it matters | Candidate |
|---|---|---|
| Framework rules for our actual stack | design-review covers look, not SvelteKit mechanics | `sveltekit-patterns` (routing, load, actions, `$app/*`, forms) |
| Discovery | 4.4M installs say agents cannot find the right skill | a `find-skills` equivalent for our local set |
| Taste/anti-default | our design-review has the rules but no style packs | optional style profiles in `assets/` |
| Security review of installed skills | registry lists audits; we have none | a `skill-audit` script (read files, flag network/exec) |

## Caveats

- Install count measures distribution, not quality; a skill with 149K stars can still be
  wrong for your stack.
- Many "design" skills are opinion packs. They help when the brief is open and hurt when
  the brief is fixed - check the brief first (see design-review's principles reference).
- Skills that run scripts or fetch the network deserve an audit before use.
