
# Pinia Stores

Global, cross-component state lives in `src/stores/` as Pinia stores named `use<Name>Store` (file `<name>.ts`).

## Structure — options API

Use the options style (`state` / `actions` / `getters`) with an explicit `State` interface.

```typescript
interface State {
  organization: OrganizationProps | null
  isLoading: boolean
}

export const useOrganizationStore = defineStore('organization', {
  state: (): State => ({
    organization: null,
    isLoading: true
  }),
  actions: {
    async init(orgId: string): Promise<void> {
      try {
        this.isLoading = true
        this.organization = await ApiService.organization.getById(orgId)
      } finally {
        this.isLoading = false
      }
    }
  },
  getters: {
    orgId(): string {
      return this.organization?.id ?? ''
    }
  }
})
```

## Rules

- Always type `state` via a dedicated `State` interface.
- Booleans use `is`/`has` prefixes (`isLoading`, `isAppListLoading`).
- Async actions wrap loading flags in `try/finally` so the flag always resets.
- Fetch data via `ApiService`, never `apiClient` directly.
- Cross-store access: call other stores inside actions (`useUiConfigStore()`), don't import their state at module scope.
- Use `pinia-plugin-persistedstate` for persistence instead of manual `localStorage` wiring where possible.
