
# Component Structure

Always use `<script setup lang="ts">` with the Composition API.

## Naming & file location

- Generic, reusable components: `Nxr[Name].vue` (e.g. `NxrPanel.vue`) in `src/components/ui/`.
- Feature components: `PascalCase` prefixed with their view/domain (e.g. `PersonalizeFormFieldCard.vue`).
- Views live in `src/views/` as `[Name]View.vue`.

## Block order inside `<script setup>`

Always keep this exact order:

1. `props`
2. `emits`
3. `models`
4. `refs`
5. `uses` (e.g. `useElementBounding()`, `useI18n()`)
6. `computed`
7. `functions` (always arrow functions!)
8. `watch` / `watchEffect`
9. `onMounted` / `onUnmounted`

## Props — reactive destructure, never `const props =`

```typescript
// ✅ GOOD
const { foo = '' } = defineProps<{ foo?: string }>()

// ❌ BAD
const props = defineProps<{ foo: string }>()
```

If a prop is only used in the template, just call `defineProps()` without assigning.

## Emits — typed tuple syntax

```typescript
const emit = defineEmits<{
  nameBlur: []
  save: [values: Record<string, string>]
}>()
```

## Models

```typescript
const options = defineModel<string[]>({ required: true })
```

## Template

Styling goes here as Tailwind utilities, never into a `<style scoped>` block —
see `styling.md`.

- Components in `PascalCase`, props in `camelCase` (eslint enforces `never` hyphenation).
- Use the shorthand binding where possible: `<PascalCase :camelCase />`.

```vue
<template>
  <NxrPanel :label @close="..." />
</template>
```

## Transitions

Use native Vue `<Transition>`. If reused, put the CSS in `styles/transitions.css`. Do not use VueUseMotion for simple transitions.
