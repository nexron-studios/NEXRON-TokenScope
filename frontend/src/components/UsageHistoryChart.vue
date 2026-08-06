<script setup lang="ts">
import { computed, ref, useTemplateRef } from 'vue'
import { useElementSize } from '@vueuse/core'
import { brandOf } from '@/theme/brands'
import type { HistoryResponse, ProviderId } from '@/api/types'

const props = defineProps<{
  history?: HistoryResponse
  hours: number
  visibleProviders: ProviderId[]
}>()

const SURFACE = '#16161a'
const PAD = { top: 12, right: 60, bottom: 20, left: 34 }
// Bewusst flach: Auf 1024 × 600 gehört die Höhe den beiden Kacheln.
const HEIGHT = 118

const wrapper = useTemplateRef<HTMLElement>('wrapper')
const { width } = useElementSize(wrapper)
const chartWidth = computed(() => Math.max(320, width.value || 640))

interface Point {
  t: number
  used: number
}

interface Series {
  provider: ProviderId
  short: string
  color: string
  label: string
  points: Point[]
  /** Jüngster Punkt – trägt Endmarker und Direktbeschriftung. */
  last: Point
}

/** Pro Anbieter genau eine Linie: das kürzeste gespeicherte Fenster. */
const series = computed<Series[]>(() => {
  const raw = props.history?.series ?? []
  const chosen = new Map<ProviderId, { rank: number; series: Series }>()

  const rank = (key: string) =>
    key === 'five_hour' || key === 'primary' ? 0 : key === 'seven_day' ? 1 : 2

  for (const entry of raw) {
    if (!props.visibleProviders.includes(entry.provider)) continue

    const entryRank = rank(entry.window_key)
    const existing = chosen.get(entry.provider)
    if (existing && existing.rank <= entryRank) continue

    const points = entry.points
      .map((point) => ({
        t: new Date(point.captured_at).getTime(),
        used: point.used_percent,
      }))
      .filter((point) => Number.isFinite(point.t))
      .sort((a, b) => a.t - b.t)

    const last = points.at(-1)
    if (!last) continue

    const brand = brandOf(entry.provider)
    chosen.set(entry.provider, {
      rank: entryRank,
      series: {
        provider: entry.provider,
        short: brand.short,
        color: brand.series,
        label: entry.label,
        points,
        last,
      },
    })
  }

  return [...chosen.values()].map((item) => item.series)
})

/** Dieselben Daten als Zeilen – Grundlage der Tabellenansicht. */
const tableRows = computed(() => {
  const columns = series.value
  const stamps = [...new Set(columns.flatMap((entry) => entry.points.map((p) => p.t)))].sort(
    (a, b) => a - b,
  )
  return stamps.map((t) => ({
    t,
    values: columns.map((entry) => entry.points.find((point) => point.t === t)?.used),
  }))
})

const domain = computed(() => {
  const end = Date.now()
  const start = end - props.hours * 3_600_000
  return { start, end }
})

const scaleX = (t: number) => {
  const { start, end } = domain.value
  const ratio = (t - start) / Math.max(1, end - start)
  return PAD.left + Math.min(1, Math.max(0, ratio)) * (chartWidth.value - PAD.left - PAD.right)
}

const scaleY = (used: number) => {
  const inner = HEIGHT - PAD.top - PAD.bottom
  return PAD.top + (1 - Math.min(100, Math.max(0, used)) / 100) * inner
}

const pathOf = (entry: Series) =>
  entry.points
    .map((point, index) => `${index === 0 ? 'M' : 'L'}${scaleX(point.t).toFixed(1)} ${scaleY(point.used).toFixed(1)}`)
    .join(' ')

const gridValues = [0, 25, 50, 75, 100]

const timeTicks = computed(() => {
  const { start, end } = domain.value
  const format = new Intl.DateTimeFormat('de-DE', {
    hour: '2-digit',
    minute: '2-digit',
    ...(props.hours > 48 ? { weekday: 'short' } : {}),
  })
  return Array.from({ length: 5 }, (_, index) => {
    const t = start + ((end - start) * index) / 4
    return { t, label: format.format(new Date(t)) }
  })
})

// --- Crosshair: funktioniert mit Maus und Finger gleichermaßen -----------
const cursorT = ref<number>()

const onPointer = (event: PointerEvent) => {
  const bounds = (event.currentTarget as SVGElement).getBoundingClientRect()
  const x = event.clientX - bounds.left
  const inner = chartWidth.value - PAD.left - PAD.right
  const ratio = (x - PAD.left) / Math.max(1, inner)
  if (ratio < -0.05 || ratio > 1.05) {
    cursorT.value = undefined
    return
  }
  const { start, end } = domain.value
  cursorT.value = start + Math.min(1, Math.max(0, ratio)) * (end - start)
}

const readout = computed(() => {
  if (cursorT.value === undefined) return undefined
  const at = cursorT.value

  const tolerance = (props.hours * 3_600_000) / 12
  const rows = series.value
    .map((entry) => {
      let nearest = entry.last
      for (const point of entry.points) {
        if (Math.abs(point.t - at) < Math.abs(nearest.t - at)) nearest = point
      }
      return { entry, point: nearest }
    })
    .filter((row) => Math.abs(row.point.t - at) < tolerance)

  if (!rows.length) return undefined
  return { x: scaleX(at), at, rows }
})

const timeFormat = new Intl.DateTimeFormat('de-DE', {
  day: '2-digit',
  month: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
})
</script>

<template>
  <section ref="wrapper" class="panel">
    <div class="panel-head">
      <div>
        <h2 class="panel-title">Verlauf</h2>
        <p class="panel-sub">Verbrauch des kürzesten Fensters, aus lokalen Snapshots</p>
      </div>

      <ul v-if="series.length" class="legend">
        <li v-for="entry in series" :key="entry.provider">
          <span class="swatch" :style="{ background: entry.color }" />
          {{ entry.short }} · {{ entry.label }}
        </li>
      </ul>
    </div>

    <div v-if="!series.length" class="empty">
      Noch keine Snapshots. Das Backend schreibt bei jedem Poll einen Punkt –
      der Verlauf füllt sich von allein.
    </div>

    <svg
      v-else
      class="chart"
      :width="chartWidth"
      :height="HEIGHT"
      :viewBox="`0 0 ${chartWidth} ${HEIGHT}`"
      role="img"
      aria-label="Verbrauchsverlauf je Anbieter"
      @pointermove="onPointer"
      @pointerdown="onPointer"
      @pointerleave="cursorT = undefined"
    >
      <g class="grid">
        <template v-for="value in gridValues" :key="value">
          <line
            :x1="PAD.left"
            :x2="chartWidth - PAD.right"
            :y1="scaleY(value)"
            :y2="scaleY(value)"
          />
          <text
            v-if="value % 50 === 0"
            :x="PAD.left - 8"
            :y="scaleY(value) + 3.5"
            text-anchor="end"
          >
            {{ value }}
          </text>
        </template>
      </g>

      <g class="ticks">
        <text
          v-for="tick in timeTicks"
          :key="tick.t"
          :x="scaleX(tick.t)"
          :y="HEIGHT - 6"
          text-anchor="middle"
        >
          {{ tick.label }}
        </text>
      </g>

      <line
        v-if="readout"
        class="crosshair"
        :x1="readout.x"
        :x2="readout.x"
        :y1="PAD.top - 4"
        :y2="HEIGHT - PAD.bottom"
      />

      <g v-for="entry in series" :key="entry.provider">
        <path :d="pathOf(entry)" fill="none" :stroke="entry.color" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
        <circle
          :cx="scaleX(entry.last.t)"
          :cy="scaleY(entry.last.used)"
          r="4"
          :fill="entry.color"
          :stroke="SURFACE"
          stroke-width="2"
        />
        <!-- Direktbeschriftung: Identität hängt nie allein an der Farbe. -->
        <text
          class="direct-label"
          :x="Math.min(chartWidth - PAD.right + 8, chartWidth - 6)"
          :y="scaleY(entry.last.used) + 4"
          :fill="entry.color"
        >
          {{ entry.short }}
        </text>
      </g>

      <g v-if="readout">
        <circle
          v-for="row in readout.rows"
          :key="row.entry.provider"
          :cx="scaleX(row.point.t)"
          :cy="scaleY(row.point.used)"
          r="4.5"
          :fill="row.entry.color"
          :stroke="SURFACE"
          stroke-width="2"
        />
      </g>
    </svg>

    <div v-if="readout" class="tooltip" :style="{ left: `${readout.x}px` }">
      <p class="tooltip-time">{{ timeFormat.format(new Date(readout.at)) }}</p>
      <p v-for="row in readout.rows" :key="row.entry.provider" class="tooltip-row">
        <span class="swatch" :style="{ background: row.entry.color }" />
        {{ row.entry.short }}
        <strong>{{ Math.round(row.point.used) }} %</strong>
      </p>
    </div>

    <!-- Tabellenansicht derselben Daten für Screenreader und Export. -->
    <table v-if="series.length" class="sr-only">
      <caption>Verbrauch in Prozent je Anbieter und Zeitpunkt</caption>
      <thead>
        <tr><th>Zeitpunkt</th><th v-for="entry in series" :key="entry.provider">{{ entry.short }}</th></tr>
      </thead>
      <tbody>
        <tr v-for="row in tableRows" :key="row.t">
          <td>{{ timeFormat.format(new Date(row.t)) }}</td>
          <td v-for="(value, index) in row.values" :key="index">
            {{ value === undefined ? '–' : `${Math.round(value)} %` }}
          </td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<style scoped>
.panel {
  position: relative;
  border: 1px solid rgb(255 255 255 / 8%);
  border-radius: 1.25rem;
  background: #16161a;
  padding: 0.85rem 1rem 0.5rem;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.panel-title {
  font-size: 0.9rem;
  font-weight: 700;
}

.panel-sub {
  margin-top: 0.1rem;
  color: #b8b8c1;
  font-size: 0.6875rem;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  color: #dadade;
  font-size: 0.6875rem;
}

.legend li {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.swatch {
  display: inline-block;
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 2px;
}

.chart {
  display: block;
  margin-top: 0.4rem;
  touch-action: none;
}

.grid line {
  stroke: rgb(255 255 255 / 7%);
  stroke-width: 1;
}

.grid text,
.ticks text {
  fill: #6c6c75;
  font-size: 10px;
}

.crosshair {
  stroke: rgb(255 255 255 / 22%);
  stroke-dasharray: 3 3;
  stroke-width: 1;
}

.direct-label {
  font-size: 11px;
  font-weight: 700;
}

.tooltip {
  position: absolute;
  top: 3.1rem;
  transform: translateX(-50%);
  border: 1px solid rgb(255 255 255 / 12%);
  border-radius: 0.6rem;
  background: rgb(10 10 12 / 94%);
  padding: 0.4rem 0.6rem;
  pointer-events: none;
  white-space: nowrap;
}

.tooltip-time {
  color: #c2c2ca;
  font-size: 0.625rem;
}

.tooltip-row {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  color: #f6f6f8;
  font-size: 0.75rem;
}

.tooltip-row strong {
  font-variant-numeric: tabular-nums;
}

.empty {
  color: #b2b2bb;
  font-size: 0.75rem;
  line-height: 1.5;
  padding: 1.6rem 0 1.8rem;
  text-align: center;
}
</style>
