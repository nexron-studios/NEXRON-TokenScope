<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import TouchSegmented from '@/components/TouchSegmented.vue'
import { useLogSummary } from '@/composables/useHistory'
import { useSettings } from '@/composables/useSettings'
import { brandOf } from '@/theme/brands'
import type { LogGroupBy } from '@/api/types'

const { settings } = useSettings()
const { summary, loading, error, load } = useLogSummary()

// Der Segmented Control arbeitet mit `string | number`; die Verengung auf
// LogGroupBy passiert beim Laden.
const groupBy = ref<string>('project')

const GROUPS: Array<{ value: LogGroupBy; label: string }> = [
  { value: 'project', label: 'Projekt' },
  { value: 'model', label: 'Modell' },
  { value: 'day', label: 'Tag' },
]

const DAY_OPTIONS = [
  { value: 7, label: '7 T' },
  { value: 30, label: '30 T' },
  { value: 90, label: '90 T' },
]

const reload = () =>
  void load(settings.value.logDays, groupBy.value as LogGroupBy)
onMounted(reload)
watch([groupBy, () => settings.value.logDays], reload)

const compact = new Intl.NumberFormat('de-DE', {
  notation: 'compact',
  maximumFractionDigits: 1,
})

/** Balkenlänge relativ zur größten Gruppe – ein Vergleich, keine Skala. */
const maxTotal = computed(() =>
  Math.max(
    1,
    ...(summary.value?.buckets ?? []).map(
      (bucket) =>
        bucket.totals.input_tokens +
        bucket.totals.output_tokens +
        bucket.totals.cache_write_tokens +
        bucket.totals.cache_read_tokens,
    ),
  ),
)

const totalOf = (totals: {
  input_tokens: number
  output_tokens: number
  cache_write_tokens: number
  cache_read_tokens: number
}) =>
  totals.input_tokens +
  totals.output_tokens +
  totals.cache_write_tokens +
  totals.cache_read_tokens
</script>

<template>
  <main class="view">
    <div class="controls">
      <TouchSegmented v-model="groupBy" label="Gruppierung" :options="GROUPS" />
      <TouchSegmented
        v-model="settings.logDays"
        label="Zeitraum"
        :options="DAY_OPTIONS"
      />
    </div>

    <section class="panel">
      <header class="panel-head">
        <div>
          <h2 class="panel-title">Token aus lokalen JSONL-Logs</h2>
          <p class="panel-sub">
            Reines Dateisystem – kein Token, kein Netzwerk, keine API, die sich ändern kann.
          </p>
        </div>
        <p v-if="summary" class="meta">
          {{ summary.scanned_files }} Dateien ·
          {{ compact.format(totalOf(summary.totals)) }} Token
        </p>
      </header>

      <p v-if="error" class="state error">{{ error }}</p>
      <p v-else-if="loading && !summary" class="state">Lese Sitzungsdateien …</p>
      <p v-else-if="summary && !summary.buckets.length" class="state">
        Für diesen Zeitraum liegen keine Sitzungen vor.
      </p>

      <!-- Alle Gruppen, nicht nur die ersten paar: auf einem grossen Schirm
           ist der Platz da, und der Rest ist erscrollbar. -->
      <ul v-else-if="summary" class="rows">
        <li v-for="bucket in summary.buckets" :key="`${bucket.provider}-${bucket.key}`">
          <div class="row-head">
            <span class="row-name">
              <span class="swatch" :style="{ background: brandOf(bucket.provider).series }" />
              {{ bucket.label }}
            </span>
            <span class="row-value">{{ compact.format(totalOf(bucket.totals)) }}</span>
          </div>
          <div class="bar-track">
            <div
              class="bar"
              :style="{
                width: `${(totalOf(bucket.totals) / maxTotal) * 100}%`,
                background: brandOf(bucket.provider).series,
              }"
            />
          </div>
          <p class="row-meta">
            {{ brandOf(bucket.provider).short }} · {{ bucket.messages }} Nachrichten ·
            {{ compact.format(bucket.totals.cache_read_tokens) }} aus Cache
          </p>
        </li>
      </ul>
    </section>
  </main>
</template>

<style scoped>
.view {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  flex: 1;
  min-height: 0;
}

.controls {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 0.75rem;
  flex-shrink: 0;
}

.panel {
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  flex: 1;
  min-height: 0;
  border: 1px solid rgb(255 255 255 / 8%);
  border-radius: 1.25rem;
  background: #16161a;
  padding: 0.9rem 1rem;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  flex-shrink: 0;
}

.panel-title {
  font-size: 0.9rem;
  font-weight: 600;
}

.panel-sub,
.meta {
  color: #7d7d86;
  font-size: 0.6875rem;
}

.meta {
  flex-shrink: 0;
  font-variant-numeric: tabular-nums;
  text-align: right;
}

.rows {
  display: grid;
  align-content: start;
  gap: 0.6rem;
  /* Die Liste bekommt den Rest der Panel-Hoehe und scrollt in sich. */
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  padding-right: 0.2rem;
  overscroll-behavior: contain;
}

.row-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
}

.row-name {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  color: #e4e4e9;
  font-size: 0.8125rem;
  font-weight: 600;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.swatch {
  flex-shrink: 0;
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 2px;
}

.row-value {
  color: #e4e4e9;
  font-size: 0.8125rem;
  font-variant-numeric: tabular-nums;
}

.bar-track {
  height: 0.5rem;
  margin-top: 0.3rem;
  overflow: hidden;
  border-radius: 999px;
  background: rgb(255 255 255 / 6%);
}

.bar {
  height: 100%;
  border-radius: 0 4px 4px 0;
  transition: width 500ms cubic-bezier(0.22, 1, 0.36, 1);
}

.row-meta {
  margin-top: 0.22rem;
  color: #75757e;
  font-size: 0.6875rem;
}

.state {
  color: #82828b;
  font-size: 0.8125rem;
  padding: 1.5rem 0;
  text-align: center;
}

.state.error {
  color: #f0a5a5;
}
</style>
