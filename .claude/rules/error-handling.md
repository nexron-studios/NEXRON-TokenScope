
# Error Handling & User Feedback

## Let the global interceptor handle API errors

`apiClient.ts` has a response interceptor that calls `handleError` for failed requests (translated toast, 401 refresh flow). Do **not** wrap every `ApiService` call in a try/catch just to show a toast.

```typescript
// ✅ GOOD — interceptor shows the error toast
const data = await ApiService.userForm.getForm(userId)

// ❌ BAD — duplicate, untranslated error handling
try {
  const data = await ApiService.userForm.getForm(userId)
} catch (e) {
  toast.error('Something went wrong')
}
```

## When you DO need local handling

- Use `{ skipGlobalErrorHandler: true }` on the request and call `handleError(error, ...)` from `@/lib/error` yourself.
- Wrap loading flags in `try/finally` so they always reset; `console.error(error)` then surface a translated message.

```typescript
isFormSaving.value = true
try {
  await ApiService.userForm.updateForm(userId, payload)
  toast.success(t('app.personalization_success'))
} catch (error) {
  console.error(error)
  toast.error(t('app.personalization_error'))
} finally {
  isFormSaving.value = false
}
```

## Rules

- Never swallow errors with an empty `catch {}`.
- All user-facing messages (success and error) go through `toast` from `vue-sonner` and must be translated with `t(...)`.
- Ignore cancellation errors (axios `ERR_CANCELED`, `AbortError`) — `handleError` already does.
