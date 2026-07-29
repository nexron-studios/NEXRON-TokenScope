<script setup lang="ts">
defineProps<{
  online: boolean
  loading: boolean
  settingsOpen: boolean
}>()

defineEmits<{
  refresh: []
  toggleSettings: []
}>()
</script>

<template>
  <header class="flex items-center justify-between gap-4">
    <div class="flex min-w-0 items-center gap-3">
      <div
        class="grid size-10 shrink-0 place-items-center rounded-xl border border-white/10 bg-white/[0.06] shadow-lg shadow-black/20"
        aria-hidden="true"
      >
        <svg viewBox="0 0 24 24" class="size-5 text-mint-400" fill="none">
          <path
            d="M4 16.5 8.2 12l3.1 2.8L19.8 6"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
          <path
            d="M15.5 6h4.3v4.3"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </div>

      <div class="min-w-0">
        <div class="flex items-center gap-2">
          <h1 class="truncate text-base font-semibold tracking-tight sm:text-lg">
            AI Usage Monitor
          </h1>
          <span
            class="hidden rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] sm:inline"
            :class="
              online
                ? 'border-emerald-400/20 bg-emerald-400/10 text-emerald-300'
                : 'border-amber-400/20 bg-amber-400/10 text-amber-300'
            "
          >
            {{ online ? 'lokal · online' : 'lokal · offline' }}
          </span>
        </div>
        <p class="mt-0.5 truncate text-xs text-slate-500">
          Persönliche Limits auf einen Blick
        </p>
      </div>
    </div>

    <div class="flex shrink-0 items-center gap-2">
      <button
        v-if="!settingsOpen"
        type="button"
        class="grid size-9 place-items-center rounded-xl border border-white/[0.08] bg-white/[0.035] text-slate-400 transition hover:border-white/15 hover:bg-white/[0.07] hover:text-white disabled:cursor-wait"
        :disabled="loading"
        aria-label="Daten aktualisieren"
        title="Jetzt aktualisieren"
        @click="$emit('refresh')"
      >
        <svg
          viewBox="0 0 24 24"
          class="size-[18px]"
          :class="{ 'animate-spin': loading }"
          fill="none"
        >
          <path
            d="M20 11a8 8 0 0 0-14.9-4M4 5v5h5m-5 3a8 8 0 0 0 14.9 4M20 19v-5h-5"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </button>

      <button
        type="button"
        class="grid size-9 place-items-center rounded-xl border transition"
        :class="
          settingsOpen
            ? 'border-mint-400/25 bg-mint-400/10 text-mint-400'
            : 'border-white/[0.08] bg-white/[0.035] text-slate-400 hover:border-white/15 hover:bg-white/[0.07] hover:text-white'
        "
        :aria-label="settingsOpen ? 'Dashboard anzeigen' : 'Einstellungen öffnen'"
        :title="settingsOpen ? 'Dashboard' : 'Einstellungen'"
        @click="$emit('toggleSettings')"
      >
        <svg v-if="!settingsOpen" viewBox="0 0 24 24" class="size-[18px]" fill="none">
          <path
            d="M12 15.2a3.2 3.2 0 1 0 0-6.4 3.2 3.2 0 0 0 0 6.4Z"
            stroke="currentColor"
            stroke-width="1.7"
          />
          <path
            d="m19.4 15 .1.1a1.8 1.8 0 0 1 0 2.5l-1.9 1.9a1.8 1.8 0 0 1-2.5 0l-.1-.1a2 2 0 0 0-3.4 1.4v.2a1.8 1.8 0 0 1-1.8 1.8H7.2A1.8 1.8 0 0 1 5.4 21v-.2A2 2 0 0 0 2 19.4l-.1.1"
            stroke="currentColor"
            stroke-width="1.7"
            stroke-linecap="round"
          />
          <path
            d="M4.6 9 4.5 9A1.8 1.8 0 0 1 4.5 6.4l1.9-1.9a1.8 1.8 0 0 1 2.5 0l.1.1a2 2 0 0 0 3.4-1.4V3A1.8 1.8 0 0 1 14.2 1.2h2.6A1.8 1.8 0 0 1 18.6 3v.2A2 2 0 0 0 22 4.6l.1-.1"
            stroke="currentColor"
            stroke-width="1.7"
            stroke-linecap="round"
          />
        </svg>
        <svg v-else viewBox="0 0 24 24" class="size-[18px]" fill="none">
          <path
            d="m15 18-6-6 6-6"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </button>
    </div>
  </header>
</template>
