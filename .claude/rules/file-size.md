# File Size & Extraction

A `.vue` file stays under **500 lines**. Views and feature components hold
markup and the wiring for that markup — not the logic behind it.

## The budget

- Hard limit: 500 lines per `.vue` file (template + script together).
- Soft signal: a `<script setup>` block past ~150 lines, or a single function
  past ~40 lines. Both mean something wants its own file, long before the hard
  limit is reached.
- When a file is already over budget, do not add to it. Extract first, then
  add.

## Where extracted code goes

| What you are extracting | Target |
| --- | --- |
| Pure functions — formatting, mapping, aggregating, sorting, math | `src/utils/<topic>.ts` |
| Reactive logic — `ref`/`computed`/`watch`, loading state, side effects | `src/composables/use<Thing>.ts` (see `composables.md`) |
| HTTP access | `src/api/services/` (see `api-services.md`) |
| Static tables, brand/model maps, constants | `src/theme/` or `src/utils/` |
| A self-contained slice of the template plus its own state | its own child component (see `component-structure.md`) |

`src/utils/` files export named arrow functions and nothing else — no Vue
imports, no module-level state, no side effects on import. That is what makes
them reusable and directly testable (see `testing.md`).

```typescript
// ✅ GOOD — src/utils/tokens.ts
export const totalOf = (totals: TokenTotals): number =>
  totals.input_tokens +
  totals.output_tokens +
  totals.cache_write_tokens +
  totals.cache_read_tokens

export const formatCompact = (locale: string, value: number): string =>
  new Intl.NumberFormat(locale, { notation: 'compact', maximumFractionDigits: 1 }).format(value)
```

```vue
<!-- ✅ GOOD — the view imports and wires, it does not compute -->
<script setup lang="ts">
import { formatCompact, totalOf } from '@/utils/tokens'
</script>
```

```vue
<!-- ❌ BAD — a 60-line builder living in the view -->
<script setup lang="ts">
const tiles = computed<Tile[]>(() => {
  // 60 lines of aggregating, labelling, formatting …
})
</script>
```

That builder takes its input as arguments and moves to `src/utils/`; the view
keeps a one-line `computed` that calls it.

## What stays in the component

- `defineProps` / `defineEmits` / `defineModel`.
- `computed`s that are a single expression over local state.
- Thin event handlers that delegate — `const reload = () => void load(days)`.
- Anything that would need three props passed into it just to be moved out.

## Extracting is not rewriting

When a function moves out, it moves as-is: same behavior, same name, plus an
explicit parameter list and a return type. Change behavior in a separate step,
never in the same edit as the move.

## Types

Types shared between the extracted file and its consumers move to
`src/types/<name>.type.ts` or `src/api/types.ts` — see `types.md`. A type used
only inside the extracted file stays there.
