# NEXRON-TokenScope

Local dashboard for Claude Code / Codex quota. FastAPI backend in `backend/`
(serves `frontend/dist` in production), Vue 3 + Vite + Tailwind 4 frontend in
`frontend/`, optional Tauri shell in `desktop/`.

Run it with `.\start.ps1` (add `-Dev` for the Vite dev server on 5173 with hot
reload; the backend stays on 8787 and serves `/api`).

## Rules

@.claude/rules/styling.md
@.claude/rules/code-style.md
@.claude/rules/component-structure.md
@.claude/rules/ui-components.md
@.claude/rules/file-size.md
@.claude/rules/composables.md
@.claude/rules/types.md
@.claude/rules/api-services.md
@.claude/rules/stores.md
@.claude/rules/error-handling.md
@.claude/rules/i18n.md
@.claude/rules/testing.md
