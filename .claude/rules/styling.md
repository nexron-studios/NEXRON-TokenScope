# Styling

Tailwind utilities in the `<template>`. Never a `<style scoped>` block.

## No `<style scoped>` — ever

```vue
<!-- ❌ BAD -->
<template>
  <div class="brand-card">…</div>
</template>

<style scoped>
.brand-card {
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}
</style>

<!-- ✅ GOOD -->
<template>
  <div class="flex h-full min-h-0 flex-col gap-[0.7rem] overflow-hidden">…</div>
</template>
```

Yes, this is more code in the template. It is still preferred: everything an
element does is readable at the element, instead of jumping between the
template and a stylesheet further down the file. Readability wins over the
shorter line — do not "improve" this by extracting classes back into a style
block.

## Conditional classes

Bind an object or array, keep the static utilities in `class`:

```vue
<div class="flex gap-2" :class="{ 'opacity-40': isLoading }">
```

## What does not go in the template

- What Tailwind cannot express — `@keyframes`, `::-webkit-scrollbar`,
  `::selection`, `@media (prefers-reduced-motion)` — belongs in
  `src/assets/main.css`.
- Design tokens (colors, font weights) go into the `@theme` block of that same
  file, never into a component.
- Values that change per element at runtime (e.g. `--brand-accent` from
  `brandVars`) stay `:style` bindings.

## Existing components

Most components in this project still carry a `<style scoped>` block. That is
legacy, not the pattern — it is being removed, not preserved.

- Never add a new `<style>` block, and never add a rule to an existing one.
  If markup being worked on needs styling, it gets Tailwind utilities.
- When a component is touched anyway, migrate the rules that belong to the
  touched markup into the template and delete them from the block. Delete the
  whole block once it is empty.
- No blanket rewrites on sight: a file nobody is working on keeps its block
  until there is a reason to open it.
- The exception stays what `main.css` owns — keyframes, pseudo-elements,
  media queries, `@theme` tokens. Those move to `src/assets/main.css`, not
  into a component.

## Debug helpers

`main.css` ships `debug-red`, `debug-blue`, … (plus `debug-outline` and
`debug-kids`) to outline and tint a box while working on layout. They are
scaffolding — remove them before committing.
