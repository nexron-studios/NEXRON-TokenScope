# UI Components

Standard interface parts are taken from a library, not drawn by hand. A button,
a dialog, a dropdown, a data table, a tooltip, a form field — these are solved
problems with accessibility, focus handling and keyboard support already in
them. Hand-rolling one means reimplementing all of that, badly.

## Where to reach first

| Library | What it covers | Preference |
| --- | --- | --- |
| [shadcn-vue](https://www.shadcn-vue.com) | Buttons, dialogs, forms, cards, sidebar, tables — the everyday primitives | ⭐⭐⭐⭐⭐ |
| [Nuxt UI](https://ui.nuxt.com) | A complete app/dashboard shell in one piece | ⭐⭐⭐⭐⭐ |
| [AI Elements](https://ai-sdk.dev/elements) | Chat, messages, conversations, AI surfaces | ⭐⭐⭐⭐⭐ |
| [Inspira UI](https://inspira-ui.com) | Animations, effect cards, backgrounds | ⭐⭐⭐⭐ |
| [Reka UI](https://reka-ui.com) | Headless primitives for components with no ready-made equivalent | ⭐⭐⭐⭐ |
| [PrimeVue / Volt](https://volt.primevue.org) | Data tables, enterprise inputs, dense grids | ⭐⭐⭐⭐ |

shadcn-vue is the default. It copies real source into the repo instead of
hiding it behind a package, which means the component can be edited like any
other file here — and it is built on Reka UI, so dropping to headless later is
a step down the same stack, not a migration.

## Pick one shell, not two

Nuxt UI and shadcn-vue both want to own the app's look. Use one of them, never
both in the same project. PrimeVue enters only for the dense-table and complex
input cases it is genuinely better at, and stays scoped to those screens.

## Adding a library

- Install through the library's own CLI or init step, so its config, theme
  tokens and aliases land correctly. Never hand-copy snippets from a docs page
  into a new file.
- shadcn-vue components land in `src/components/ui/` — the same place
  `component-structure.md` already points at.
- Add one component, not the catalogue. `npx shadcn-vue@latest add button` when
  a button is needed, not the full set up front.
- Check `frontend/package.json` before installing: something suitable may
  already be there.

## What is still written by hand

The library is for generic parts. These are not generic and stay ours:

- **Touch-panel controls** — `TouchToggle`, `TouchSegmented`. Their 3.5 rem hit
  targets exist because the target device is a 7" panel, and a stock switch
  does not carry that.
- **Domain visualisation** — `ProviderCard`, `UsageHistoryChart`,
  `ActivityHeatmap`, `UsageMeter`. Brand colours, quota semantics and the
  1024 × 600 layout are the point of these components.

When something is close to a library component but not quite, take the library
component and adapt it. Starting from scratch is the last option, not the
first.

## Icons

Icons come from `@lucide/vue`, imported by name and sized with Tailwind:

```vue
<script setup lang="ts">
import { RefreshCw } from '@lucide/vue'
</script>

<template>
  <RefreshCw class="size-5" :class="{ 'animate-spin': loading }" aria-hidden="true" />
</template>
```

Never inline a hand-drawn `<svg>` path for something Lucide already has. Mark
icons `aria-hidden="true"` when a label sits next to them; give the *button*
an `aria-label` when it does not. Outline icons need room — below roughly
0.8 rem they turn to mush, so size up rather than shrinking the stroke.

## The house rules still apply

A library component does not suspend the rest of this ruleset:

- Styling stays Tailwind utilities in the template, never `<style scoped>` —
  see `styling.md`.
- Every label, placeholder and message goes through `t(...)` — see `i18n.md`.
- Wrapper components follow `component-structure.md` (`<script setup lang="ts">`,
  block order, reactive prop destructure).
- Everything must work offline. This app ships to a local panel: no CDN
  imports, no runtime font or asset fetches.
