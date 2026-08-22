
# Code Style Guide

## Single responsibility

Each component, composable, and function does one thing. If you need "and" to describe it, split it.

- Components: extract sub-components when a `<template>` grows large or handles multiple concerns.
- Functions: keep them short and focused. If a function needs scrolling, break it up.
- Files: `.vue` files stay under 500 lines. Logic that outgrows the component moves into `src/utils/` or a composable — see `file-size.md`.

## Always use arrow functions

All functions are written in arrow notation — in components, composables, and utils.

```typescript
// ✅ GOOD
const getUsers = () => { ... }

// ❌ BAD
function getUsers() { ... }
```

## Early returns

Avoid nested conditionals. Return as soon as a condition is met.

```typescript
// ✅ GOOD
if (!userInput.value) return
if (isDuplicate(userInput.value)) return
options.value.push(userInput.value)
```

## Naming

- Variables and functions: `camelCase`, descriptive verbs for functions (`getForm`, `handleSave`).
- Components & types: `PascalCase`. Types/interfaces end in `Props`/`Type` per their file convention.
- Booleans: always prefix with `is`, `has`, `can`, `should` (`isLoading`, `hasAttribute`).

## No magic values

Extract repeated literals to named constants (`SCREAMING_SNAKE_CASE` for module-level constants).

## Immutability preference

Prefer `const` over `let`. Avoid mutating props directly.

## Comments — explain why, not what

Code should be self-explanatory. Never add comments that narrate what the code does. Only explain intent, trade-offs, or non-obvious constraints.

## Imports

Use the `@/` alias for `src` imports. Import only what you use.
