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

Components that still carry a scoped block are not rewritten on sight. When
their markup is being worked on anyway, the styling that is touched moves into
the template.

## Debug helpers

`main.css` ships `debug-red`, `debug-blue`, … (plus `debug-outline` and
`debug-kids`) to outline and tint a box while working on layout. They are
scaffolding — remove them before committing.
