
# Testing (Vitest)

## Location: `__test__` next to the code

Put spec files in a `__test__` folder beside the code they test, one spec per unit.

```
api/services/
  helper.service.ts
  __test__/
    helper.service.spec.ts
```

## File naming

- One spec per unit: `<name>.spec.ts` matching the file under test.
- Import the unit under test with a relative path (`from '@/api/services/helper.service'` or `'../helper.service'`).

## Structure

- Top-level `describe`: the function/class/composable name.
- `it`: one behavior per test, phrased as a sentence ("should filter apps based on search text in title").
- Use `describe`, `it`, `expect` (and `beforeEach`, `vi` when needed) from `vitest`.

```typescript
import { getFilteredAndGroupedApps } from '@/api/services/helper.service'
import { describe, expect, it } from 'vitest'

describe('getFilteredAndGroupedApps', () => {
  it('should return all apps when search text is empty', () => {
    const result = getFilteredAndGroupedApps(mockApps, '')
    expect(Object.keys(result)).toContain('Category 1')
  })
})
```

## Rules

- Arrange–Act–Assert; one focus per `it`.
- Test public behavior (return values, emitted events, calls to mocks), not implementation details.
- Mock dependencies with `vi.fn()`; keep tests fast and deterministic.
- For i18n-dependent code, use the real `i18n.global.t` from `@/i18n` so keys resolve.
