# Framework rules by installed major

Never write the style you remember. Read the installed version, then write that style.
`pkgcheck.py project . --rules` prints exactly these lines from `node_modules`.

## Svelte 5 (runes) vs Svelte 4 (legacy)

Verified against <https://svelte.dev/docs/svelte/what-are-runes> and the "Legacy APIs"
section of the same docs, plus `svelte@5.57.3` on npm.

| Svelte 5 (write this) | Svelte 4 / legacy (do not write in new code) |
|---|---|
| `let x = $state(0)` | `let x = 0` (implicitly reactive) |
| `let y = $derived(x * 2)` | `$: y = x * 2` |
| `$effect(() => { ... })` | `$: { ... }` side effects, `onMount` for subscriptions |
| `let { a, b = 1 } = $props()` | `export let a; export let b = 1;` |
| `let { value = $bindable() } = $props()` | `export let value` + manual binding |
| `<button onclick={fn}>` | `<button on:click={fn}>` |
| `{#snippet row(item)}...{/snippet}` + `{@render row(x)}` | `<slot>` / `<svelte:fragment>` |
| `mount(App, { target })` | `new App({ target })` |
| `$inspect(x)` for debugging | `console.log` in `$:` |

Runes list: `$state`, `$derived`, `$effect`, `$props`, `$bindable`, `$inspect`, `$host`.
They are compiler keywords, not imports.

## SvelteKit 3 vs 2

Verified from `@sveltejs/kit@3.2.0` type declarations.

| Kit 3 (write this) | Kit 2 (older) |
|---|---|
| `$app/state` -> `page`, `navigating`, `updated` | `$app/stores` -> `$page`, `$navigating` |
| `$app/server` remote functions: `query`, `form`, `command`, `prerender` | none |
| `@sveltejs/kit/node`: `getRequest`, `setResponse` | same idea, older shape |
| `resolve()` from `$app/paths` | `base` string concatenation |
| env via `src/env.ts` + `defineEnvVars` (`@sveltejs/kit/env`), read with `$app/env/private` or `$app/env/public` | env via `$env/dynamic/*` and `$env/static/*` |

If the project is on Kit 2, do not import `$app/state` or remote functions.

## Tailwind 4 vs 3

Verified against <https://tailwindcss.com/docs/upgrade-guide> (v4.3 docs).

| Tailwind 4 (write this) | Tailwind 3 (do not mix in) |
|---|---|
| `@import "tailwindcss";` | `@tailwind base; @tailwind components; @tailwind utilities;` |
| theme in CSS with `@theme { --color-*: ... }` | `tailwind.config.js` theme object |
| `@utility tab-4 { ... }` | `@layer utilities { .tab-4 { ... } }` |
| `bg-red-500!` (suffix) | `!bg-red-500` (prefix, deprecated) |
| `shadow-xs` / `rounded-sm` / `ring-3` / `outline-hidden` | `shadow-sm` / `rounded` / `ring` / `outline-none` |
| `bg-(--brand-color)` | `bg-[--brand-color]` |
| `@reference "<main stylesheet>";` inside a Svelte `<style>` before `@apply` | plain `@apply` without reference |
| Vite plugin `@tailwindcss/vite` | PostCSS plugin `tailwindcss` + `postcss-import` + `autoprefixer` |
| `hover` only on hover-capable devices | `hover` on tap |

Also gone in v4: `corePlugins`, `resolveConfig`, Sass/Less/Stylus pipelines, the
`container` options.

`@reference` takes the stylesheet that does `@import "tailwindcss"` plus your `@theme`,
resolved relative to the component file - not the project root:

| Setup | `@reference` from the component |
|---|---|
| `sv create` default: CSS is `src/routes/layout.css` | `"./layout.css"` from `src/routes/Foo.svelte` |
| same CSS, component in `src/lib` | `"../routes/layout.css"` |
| SvelteKit 2 layout with `src/app.css` | `"../app.css"` from `src/lib` |
| Tailwind CLI `-i ./layout.css`, file at repo root | `"../../layout.css"` from `src/lib` |
| anything, via `package.json` `imports` | `"#layout.css"` |
| default theme only, no `@theme` | `"tailwindcss"` |

Subpath imports work with the CLI, Vite and PostCSS, so `"#layout.css"` avoids relative
paths entirely - `sv create` already writes `imports` aliases such as `#lib/*`. Getting the
path wrong fails silently: `@apply` compiles with no theme values.

## Scaffolding with `sv` (verified 2026-11-14)

Run `--help` before quoting a scaffold command; add-ons and option names change often:

```bash
bunx sv create --help
npx sv create --help      # on Windows PowerShell use npx.cmd: npx.ps1 is blocked by ExecutionPolicy
```

`sv create` accepts `--template minimal|demo|library|addon`, `--types ts|jsdoc`,
`--install npm|yarn|pnpm|pnpm-rush|bun|deno|nub|aube` (or `--no-install`), and `--add` with
names such as `prettier`, `eslint`, `vitest`, `playwright`, `tailwindcss`, `sveltekit-adapter`,
`drizzle`, `better-auth`, `mdsvex`, `paraglide`, `storybook`, `ai-tools`, `experimental`.
Options go inline: `--add drizzle="database:postgresql+client:postgres.js"`.

What a minimal TypeScript scaffold actually produces (checked by running it, `--no-install`):

- **No `svelte.config.js`.** The adapter, `compilerOptions.runes` and `experimental` flags live
  in `vite.config.ts` inside `sveltekit({ ... })`.
- Tailwind comes from the `tailwindcss` add-on as `@tailwindcss/vite` in `vite.config.ts`, with
  `@import 'tailwindcss'` in `src/routes/layout.css`. There is no `app.css`, no
  `tailwind.config.js` and no PostCSS config.
- `--add experimental="features:remoteFunctions"` writes `experimental: { remoteFunctions: true }`
  into the `sveltekit()` options; without it the flag is absent. Read `vite.config.ts`, not memory.
- `package.json` ships `imports` aliases (`#lib`, `#lib/*`) and `check`/`check:watch` scripts.
- Non-interactive: pass `--template`, `--types`, `--add` and `--install`/`--no-install` together.

## AI SDK pairing

Verified from npm metadata on 2026-11-14:

- `@ai-sdk/svelte@5.0.173` depends on `ai@7.0.173` (exact pin) and peers `svelte ^5.31.0`
- `ai-sdk-ollama@4.6.3` peers `ai ^7.0.137`
- both require node >= 22

Never upgrade one of the three alone. Check with `pkgcheck.py project . --rules`.

## AI SDK 4 -> 5 (still required for ai 7)

Verified against <https://ai-sdk.dev/docs/migration-guides/migration-guide-5-0>.

| Old (4.x) | Write instead (5+) |
|---|---|
| `maxTokens: 1024` | `maxOutputTokens: 1024` |
| `convertToCoreMessages(...)` | `await convertToModelMessages(...)` (async in ai 7) |
| `CoreMessage` | `ModelMessage` |
| `Message` (UI) | `UIMessage` (has `parts`, not `content`) |
| `maxSteps: 5` | `stopWhen: isStepCount(5)` |
| `providerMetadata` input | `providerOptions` input |
| tool `parameters:` | tool `inputSchema:` |
| tool part `args` / `result` | `input` / `output` |
| `part.reasoning` on reasoning parts | `part.text` |
| `mimeType` | `mediaType` |
| `addToolResult(...)` | `addToolOutput({ tool, toolCallId, output })` |
| `initialMessages:` | `messages:` |
| `append({ role, content })` | `sendMessage({ text })` |
| `reload()` | `regenerate()` |
| `isLoading` | `status` |
| `useChat({ api })` (React/Vue) | `useChat({ transport: new DefaultChatTransport({ api }) })` |
| `import { useChat } from 'ai/react'` | `from '@ai-sdk/react'` |
| `import { x } from 'ai/rsc'` | `from '@ai-sdk/rsc'` |
| `Chat({ ... })` (Svelte) | `new Chat({ ... })` |
| `StreamData`, `writeData`, `writeMessageAnnotation` | `createUIMessageStream` + data parts |
| `result.toUIMessageStreamResponse()` | `createUIMessageStreamResponse({ stream: toUIMessageStream({ stream: result.stream }) })` (deprecated in ai 7) |
| `toolCallStreaming` | removed (always on) |

In Svelte there is **no `useChat`**. `@ai-sdk/svelte@5.0.173` ships `Chat`, `Completion`,
`createAIContext` and `StructuredObject` only (verified from its `dist/index.d.ts`); use the
class - `import { Chat } from '@ai-sdk/svelte'` then `new Chat({ transport })`. `useChat` is a
hook that exists only in `@ai-sdk/react` and `@ai-sdk/vue`.

`pkgcheck.py scan .` detects the mechanical renames only - `maxTokens`,
`convertToCoreMessages`, `CoreMessage`, `ai/react`, `ai/rsc`, `maxSteps`, `addToolResult`,
`initialMessages`, `append(`, `toUIMessageStreamResponse`, and `Chat({` without `new`. It
cannot see type-only or option renames (`UIMessage`, `mimeType`, `providerOptions`,
`inputSchema`); read the installed types for those, and treat `append(` hits as candidates
because the rule is regex-based.

## Icons

- `@lucide/svelte` (current) vs `lucide-svelte` (deprecated on npm, use the scoped name).

## How to apply

1. Run `pkgcheck.py project . --rules` and paste the lines into the answer's context.
2. Before writing a component, confirm the syntax in that list, not from memory.
3. If a file already uses the old style in a new-major project, call it out as a defect
   instead of copying it.
