
# API Services

All HTTP access goes through the service layer in `src/api/services/`. Components and composables call `ApiService.<domain>.<method>()` — never `apiClient` directly.

## File layout

- One file per domain: `<domain>.service.ts` (e.g. `userForm.service.ts`, `organization.service.ts`).
- Export a plain object named `<domain>Service`, then register it in `src/api/index.ts` on the `ApiService` aggregator.

```typescript
import apiClient from '@/api/apiClient'

export interface UserFormResponse {
  formFields: Record<string, string | null>
}

export const userFormService = {
  async getForm(userId: string): Promise<UserFormResponse> {
    const { data } = await apiClient.get<UserFormResponse>(`/users/${userId}/form`)
    return data
  },
  async updateForm(userId: string, payload: Record<string, string | null>): Promise<UserFormResponse> {
    const { data } = await apiClient.patch<UserFormResponse>(`/users/${userId}/form`, { formFields: payload })
    return data
  }
}
```

## Rules

- Always type the request generic and the return value: `apiClient.get<ResponseType>(...)` returning `Promise<ResponseType>`.
- Destructure `{ data }` from the response and return only `data` — never leak the full axios response.
- Methods are `async` arrow/shorthand methods with explicit return types.
- Do not add try/catch for toasts here — the global interceptor in `apiClient.ts` handles errors. Pass `{ skipGlobalErrorHandler: true }` only when the caller handles the error itself.
- Co-locate request/response `interface`s in the service file (or in `src/types/` if shared widely).
