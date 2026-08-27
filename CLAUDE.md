# NEXRON-TokenScope

Local dashboard for Claude Code / Codex quota. FastAPI backend in `backend/`
(serves `frontend/dist` in production), Vue 3 + Vite + Tailwind 4 frontend in
`frontend/`, optional Tauri shell in `desktop/`.

Run it with `.\start.ps1` (add `-Dev` for the Vite dev server on 5173 with hot
reload; the backend stays on 8787 and serves `/api`).

## What deviates here

- **The web conventions apply to `frontend/` only.** `backend/` is FastAPI in
  Python and `desktop/` is Tauri — Vue, Pinia, Tailwind and vue-i18n have no
  bearing there, and the NestJS rules are not loaded at all.
- **Every `.vue` file still carries a `<style scoped>` block** (15 of 15). That is
  legacy, not the pattern. Migrate the rules for markup you are touching anyway
  and delete the block once it is empty — no blanket rewrites on sight.
- Per-element runtime values come from `brandVars` as `:style` bindings.

Everything else is loaded globally from `~/.claude/rules/` — nothing to import
here.
