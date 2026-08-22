
# Composables

Reusable reactive logic lives in `src/composables/` as composables named `use<Thing>` (e.g. `useThreeScene`).

## Structure

- Export a single named function `export function useThing() { ... }`.
- Inside, declare `refs` / `computed` first, then arrow-function handlers, then return a flat object of everything the consumer needs.
- Booleans use `is`/`has` prefixes (`isFormLoading`, `isFormSaving`).

```typescript
export function usePersonalizationForm() {
  const { t } = useI18n()
  const isFormLoading = ref(false)
  const formValues = ref<Record<string, string>>({})

  const isFormDirty = computed(() => { ... })

  const loadUserForm = async () => { ... }
  const handleSavePersonalization = async () => { ... }

  return { formValues, isFormLoading, isFormDirty, loadUserForm, handleSavePersonalization }
}
```

## Rules

- Composables own state + side effects; components stay thin and consume the returned API.
- Call API through `ApiService`, never `apiClient` directly from a composable.
- Use `@vueuse/core` helpers (`whenever`, `watchPausable`, etc.) instead of hand-rolling equivalents.
- Show user feedback with `toast` from `vue-sonner`; translate every message with `t(...)`.
