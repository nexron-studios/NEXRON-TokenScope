<script setup lang="ts">
import { computed, ref } from 'vue'
import ProviderMark from '@/components/ProviderMark.vue'
import TouchSegmented from '@/components/TouchSegmented.vue'
import TouchToggle from '@/components/TouchToggle.vue'
import { useSettings } from '@/composables/useSettings'
import { BRANDS } from '@/theme/brands'
import type { HealthResponse, ProviderId } from '@/api/types'

const props = defineProps<{ health?: HealthResponse }>()
const emit = defineEmits<{ changed: [] }>()

const { settings, resetSettings } = useSettings()

type Section = 'anzeige' | 'daten' | 'dienst'
const section = ref<Section>('anzeige')

const SECTIONS: Array<{ id: Section; label: string; hint: string }> = [
  { id: 'anzeige', label: 'Anzeige', hint: 'Panel & Lesbarkeit' },
  { id: 'daten', label: 'Daten', hint: 'Intervall & Zeiträume' },
  { id: 'dienst', label: 'Dienst', hint: 'Quellen & Diagnose' },
]

const INTERVALS = [
  { value: 30, label: '30 s' },
  { value: 60, label: '1 min' },
  { value: 300, label: '5 min' },
  { value: 900, label: '15 min' },
]

const RANGES = [
  { value: 6, label: '6 Std.' },
  { value: 24, label: '24 Std.' },
  { value: 72, label: '3 T' },
  { value: 168, label: '7 T' },
]

const PROVIDERS: ProviderId[] = ['claude', 'codex']

const SOURCE_LABELS: Record<string, string> = {
  claude_credentials: 'Claude · Credentials',
  claude_logs: 'Claude · Sitzungslogs',
  codex_credentials: 'Codex · auth.json',
  codex_logs: 'Codex · Rollout-Logs',
}

const resetPending = ref(false)

const handleReset = () => {
  if (!resetPending.value) {
    resetPending.value = true
    return
  }
  resetSettings()
  resetPending.value = false
  emit('changed')
}

const lastPoll = computed(() => {
  const value = props.health?.last_poll_at
  if (!value) return 'noch nie'
  return new Intl.DateTimeFormat('de-DE', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(value))
})
</script>

<template>
  <main class="view">
    <!-- Vertikale Leiste statt Tab-Reihe: Auf 1024 × 600 bleibt so rechts
         voller Platz für die Bedienelemente, ohne dass gescrollt wird. -->
    <nav class="rail" aria-label="Einstellungsbereiche">
      <button
        v-for="entry in SECTIONS"
        :key="entry.id"
        type="button"
        class="rail-item"
        :class="{ active: section === entry.id }"
        :aria-current="section === entry.id ? 'true' : undefined"
        @click="section = entry.id"
      >
        <span class="rail-label">{{ entry.label }}</span>
        <span class="rail-hint">{{ entry.hint }}</span>
      </button>

      <button
        type="button"
        class="rail-item reset"
        :class="{ armed: resetPending }"
        @click="handleReset"
        @blur="resetPending = false"
      >
        <span class="rail-label">{{ resetPending ? 'Wirklich?' : 'Zurücksetzen' }}</span>
        <span class="rail-hint">Nur lokale Anzeigeoptionen</span>
      </button>
    </nav>

    <section class="pane">
      <template v-if="section === 'anzeige'">
        <div class="stack">
          <TouchToggle
            v-model="settings.largeText"
            label="Große Schrift"
            hint="Kennzahlen aus zwei Metern Abstand ablesbar"
          />
          <TouchToggle
            v-model="settings.kioskMode"
            label="Kiosk-Modus"
            hint="Mauszeiger aus, keine Hover-Zustände"
          />
          <TouchToggle
            v-model="settings.nightMode"
            label="Nachtmodus"
            hint="Dimmt das Panel, ohne die Hintergrundbeleuchtung zu ändern"
          />
        </div>

        <div class="stack">
          <p class="caption">Sichtbare Anbieter</p>
          <button
            v-for="id in PROVIDERS"
            :key="id"
            type="button"
            class="provider"
            :class="{ off: !settings.enabledProviders[id] }"
            role="switch"
            :aria-checked="settings.enabledProviders[id]"
            @click="settings.enabledProviders[id] = !settings.enabledProviders[id]"
          >
            <ProviderMark class="chip" :provider="id" :size="22" />
            <span class="provider-name">{{ BRANDS[id].name }}</span>
            <span class="provider-state">
              {{ settings.enabledProviders[id] ? 'sichtbar' : 'aus' }}
            </span>
          </button>
        </div>
      </template>

      <template v-else-if="section === 'daten'">
        <div class="stack">
          <TouchToggle
            v-model="settings.autoRefresh"
            label="Automatisch aktualisieren"
            hint="Das Backend pollt unabhängig davon weiter"
          />
          <TouchSegmented
            v-model="settings.refreshIntervalSeconds"
            label="Abholintervall"
            :options="INTERVALS"
          />
        </div>

        <div class="stack">
          <TouchSegmented
            v-model="settings.historyHours"
            label="Verlauf im Dashboard"
            :options="RANGES"
          />
          <p class="note">
            Der Verlauf kommt aus der lokalen SQLite-Datei. Jeder Poll schreibt
            einen Punkt; die Daten verlassen das Gerät nicht.
          </p>
        </div>
      </template>

      <template v-else>
        <div class="stack">
          <p class="caption">Gefundene Quellen</p>
          <ul class="sources">
            <li v-for="(available, key) in health?.sources ?? {}" :key="key">
              <span class="dot" :class="available ? 'on' : 'off'" />
              {{ SOURCE_LABELS[key] ?? key }}
              <span class="source-state">{{ available ? 'vorhanden' : 'fehlt' }}</span>
            </li>
          </ul>
        </div>

        <div class="stack">
          <dl class="facts">
            <div><dt>Letzter Poll</dt><dd>{{ lastPoll }}</dd></div>
            <div>
              <dt>Backend</dt>
              <dd>{{ health ? `v${health.version}` : 'nicht erreichbar' }}</dd>
            </div>
            <div>
              <dt>Bindung</dt>
              <dd :class="{ warn: health && !health.loopback_only }">
                {{ health?.loopback_only === false ? 'im Netz erreichbar' : 'nur localhost' }}
              </dd>
            </div>
            <div>
              <dt>Verlauf</dt>
              <dd>{{ health?.history_enabled ? 'SQLite aktiv' : 'nur Cache' }}</dd>
            </div>
          </dl>

          <p v-if="health?.last_poll_error" class="note warn">
            {{ health.last_poll_error }}
          </p>
          <p class="note">
            Tokens werden bei jedem Poll frisch aus den CLI-Dateien gelesen und
            nie gespeichert, geloggt oder an das Frontend gegeben.
          </p>
        </div>
      </template>
    </section>
  </main>
</template>

<style scoped>
.view {
  display: grid;
  grid-template-columns: 13.5rem minmax(0, 1fr);
  gap: 0.75rem;
  flex: 1;
  min-height: 0;
}

.rail {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.rail-item {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  min-height: 3.5rem;
  border: 1px solid rgb(255 255 255 / 8%);
  border-radius: 0.9rem;
  background: rgb(255 255 255 / 3%);
  color: #ccccd3;
  padding: 0.55rem 0.85rem;
  text-align: left;
  touch-action: manipulation;
  transition: background 140ms ease, color 140ms ease;
}

.rail-item.active {
  background: rgb(255 255 255 / 11%);
  color: #fff;
}

.rail-item.reset {
  margin-top: auto;
  border-color: rgb(208 59 59 / 25%);
}

.rail-item.reset.armed {
  background: rgb(208 59 59 / 14%);
  color: #f8c8c8;
}

.rail-label {
  font-size: 0.875rem;
  font-weight: 700;
}

.rail-hint {
  color: #b2b2bb;
  font-size: 0.6875rem;
}

.pane {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem 1rem;
  align-content: start;
  overflow-y: auto;
  border: 1px solid rgb(255 255 255 / 8%);
  border-radius: 1.25rem;
  background: #16161a;
  padding: 0.9rem 1rem;
}

.stack {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  min-width: 0;
}

.caption {
  color: #bcbcc5;
  font-size: 0.6875rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.provider {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  min-height: 3.25rem;
  border: 1px solid rgb(255 255 255 / 8%);
  border-radius: 0.9rem;
  background: rgb(255 255 255 / 3%);
  color: #f4f4f6;
  padding: 0 0.9rem;
  touch-action: manipulation;
}

.provider.off {
  color: #acacb6;
}

.provider.off .chip {
  opacity: 0.35;
}

.chip {
  flex-shrink: 0;
}

.provider-name {
  font-size: 0.875rem;
  font-weight: 700;
}

.provider-state {
  margin-left: auto;
  color: #bababf;
  font-size: 0.75rem;
}

.sources {
  display: grid;
  gap: 0.4rem;
}

.sources li {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  border: 1px solid rgb(255 255 255 / 7%);
  border-radius: 0.7rem;
  color: #ececef;
  font-size: 0.8125rem;
  padding: 0.55rem 0.75rem;
}

.dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 999px;
  flex-shrink: 0;
}

.dot.on {
  background: #0ca30c;
}

.dot.off {
  background: #d03b3b;
}

.source-state {
  margin-left: auto;
  color: #bababf;
  font-size: 0.75rem;
}

.facts {
  display: grid;
  gap: 0.4rem;
}

.facts div {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
  border-bottom: 1px solid rgb(255 255 255 / 6%);
  padding-bottom: 0.35rem;
}

.facts dt {
  color: #bcbcc5;
  font-size: 0.75rem;
}

.facts dd {
  color: #f4f4f6;
  font-size: 0.8125rem;
  font-variant-numeric: tabular-nums;
}

.note {
  color: #b2b2bb;
  font-size: 0.75rem;
  line-height: 1.4;
}

.note.warn,
.facts dd.warn {
  color: #fab219;
}
</style>
