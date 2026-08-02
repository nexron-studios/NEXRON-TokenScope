<script setup lang="ts">
import { computed } from 'vue'
import { useNow } from '@vueuse/core'

export type ViewId = 'dashboard' | 'logs' | 'settings'

defineProps<{
  view: ViewId
  loading: boolean
  connected: boolean
  demo: boolean
}>()

defineEmits<{ navigate: [ViewId]; refresh: [] }>()

const now = useNow({ interval: 10_000 })
const clock = computed(() =>
  new Intl.DateTimeFormat('de-DE', { hour: '2-digit', minute: '2-digit' }).format(
    now.value,
  ),
)

const TABS: Array<{ id: ViewId; label: string }> = [
  { id: 'dashboard', label: 'Kontingent' },
  { id: 'logs', label: 'Verbrauch' },
  { id: 'settings', label: 'Einstellungen' },
]
</script>

<template>
  <header class="head">
    <div class="brand">
      <span class="clock">{{ clock }}</span>
      <span class="divider" />
      <span class="state" :class="connected ? 'up' : 'down'">
        <span class="dot" />
        {{ connected ? 'Dienst lokal' : 'Kein Backend' }}
      </span>
      <span v-if="demo" class="demo">Demo</span>
    </div>

    <nav class="tabs">
      <button
        v-for="tab in TABS"
        :key="tab.id"
        type="button"
        class="tab"
        :class="{ active: view === tab.id }"
        :aria-current="view === tab.id ? 'page' : undefined"
        @click="$emit('navigate', tab.id)"
      >
        {{ tab.label }}
      </button>

      <button
        type="button"
        class="tab icon"
        :disabled="loading"
        aria-label="Jetzt aktualisieren"
        @click="$emit('refresh')"
      >
        <svg viewBox="0 0 24 24" class="size-5" :class="{ spin: loading }" fill="none">
          <path
            d="M20 11a8 8 0 0 0-14.9-4M4 5v5h5m-5 3a8 8 0 0 0 14.9 4M20 19v-5h-5"
            stroke="currentColor"
            stroke-width="1.9"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </button>
    </nav>
  </header>
</template>

<style scoped>
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  height: 3.625rem;
  flex-shrink: 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  min-width: 0;
}

.clock {
  font-size: 1.35rem;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.divider {
  width: 1px;
  height: 1.1rem;
  background: rgb(255 255 255 / 12%);
}

.state {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  color: #8b8b94;
  font-size: 0.75rem;
  font-weight: 600;
}

.dot {
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 999px;
  background: currentColor;
}

.state.up {
  color: #4f9d6d;
}

.state.down {
  color: #d03b3b;
}

.demo {
  border: 1px solid rgb(250 178 25 / 45%);
  border-radius: 999px;
  color: #fab219;
  font-size: 0.625rem;
  font-weight: 700;
  letter-spacing: 0.09em;
  padding: 0.15rem 0.5rem;
  text-transform: uppercase;
}

.tabs {
  display: flex;
  gap: 0.3rem;
  border: 1px solid rgb(255 255 255 / 8%);
  border-radius: 0.9rem;
  background: rgb(255 255 255 / 3%);
  padding: 0.25rem;
}

.tab {
  min-height: 3rem;
  border: 0;
  border-radius: 0.65rem;
  background: transparent;
  color: #9a9aa3;
  font-size: 0.8125rem;
  font-weight: 600;
  padding: 0 0.95rem;
  touch-action: manipulation;
  transition: background 140ms ease, color 140ms ease;
}

.tab:active {
  background: rgb(255 255 255 / 6%);
}

.tab.active {
  background: rgb(255 255 255 / 12%);
  color: #fff;
}

.tab.icon {
  display: grid;
  place-items: center;
  min-width: 2.75rem;
  padding: 0;
}

.tab:disabled {
  opacity: 0.5;
}

.spin {
  animation: spin 900ms linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
