
# Type Definitions

Shared types live in `src/types/` as `<name>.type.ts`. Types used only inside one service/composable may stay co-located in that file.

## Conventions

- Use `interface` for object shapes; suffix data shapes with `Props` (e.g. `OrganizationFormFieldProps`) and payloads with `Payload`.
- Use `type` for unions and derived/utility types (`FormFieldType = 'input' | 'textarea' | 'select'`).
- No TS `enum` — use a `const` list + derived type so it works at runtime and stays tree-shakeable.

```typescript
// ✅ GOOD
export const fieldTypeList = ['input', 'textarea', 'select'] as const
export type FormFieldType = (typeof fieldTypeList)[number]

// ❌ BAD
export enum FormFieldType { Input, Textarea, Select }
```

## Documentation

Add a JSDoc comment for non-obvious fields, especially server-generated or conditionally-relevant ones.

```typescript
export interface OrganizationFormFieldProps {
  /** Unique identifier for the form field (server generated) */
  id?: string
  /** Selectable values, only relevant for the `select` field type */
  options?: string[] | null
}
```

## Nullability

- Optional/absent → `field?: T`.
- Explicitly nullable from the API → `field: T | null`.
- Combine when both apply (`options?: string[] | null`).
