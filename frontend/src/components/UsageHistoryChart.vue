<script setup lang="ts">
import { computed, ref, useTemplateRef } from "vue";
import { useElementSize, useNow } from "@vueuse/core";
import { brandOf } from "@/theme/brands";
import { useI18n } from "@/composables/useI18n";
import type { HistoryResponse, ProviderId } from "@/api/types";
import { ChartLine, Inbox } from "@lucide/vue";

const props = defineProps<{
  history?: HistoryResponse;
  hours: number;
  visibleProviders: ProviderId[];
  loading?: boolean;
}>();

const { language, locale, t } = useI18n();

const SURFACE = "#16161a";
const PAD = { top: 12, right: 60, bottom: 20, left: 34 };
const wrapper = useTemplateRef<HTMLElement>("wrapper");
const { width } = useElementSize(wrapper);

/*
 * Die Zeichenfläche misst sich selbst, statt eine feste Höhe zu setzen: Die
 * Kacheln nehmen sich oben, was sie brauchen, der Verlauf bekommt den Rest.
 * So bleibt auf 1024 × 600 (mit Banner sogar knapper) alles vollständig,
 * während auf einem hohen Fenster kein leerer Streifen stehen bleibt.
 * Rückkopplung ist ausgeschlossen: `.plot` bezieht seine Höhe aus dem
 * Flexlayout, nicht aus dem SVG darin.
 */
const plot = useTemplateRef<HTMLElement>("plot");
const { height: plotHeight } = useElementSize(plot);
const HEIGHT = computed(() => Math.round(plotHeight.value) || 118);
const chartNow = useNow({ interval: 60_000 });
const chartWidth = computed(() => Math.max(320, width.value || 640));

interface Point {
  t: number;
  used: number;
}

interface Series {
  provider: ProviderId;
  short: string;
  color: string;
  label: string;
  points: Point[];
  /** Jüngster Punkt – trägt Endmarker und Direktbeschriftung. */
  last: Point;
}

/** Pro Anbieter genau eine Linie: das kürzeste gespeicherte Fenster. */
const series = computed<Series[]>(() => {
  const raw = props.history?.series ?? [];
  const chosen = new Map<ProviderId, { rank: number; series: Series }>();

  const rank = (key: string) =>
    key === "five_hour" || key === "primary" ? 0 : key === "seven_day" ? 1 : 2;

  for (const entry of raw) {
    if (!props.visibleProviders.includes(entry.provider)) continue;

    const entryRank = rank(entry.window_key);
    const existing = chosen.get(entry.provider);
    if (existing && existing.rank <= entryRank) continue;

    const points = entry.points
      .map((point) => ({
        t: new Date(point.captured_at).getTime(),
        used: point.used_percent,
      }))
      .filter((point) => Number.isFinite(point.t))
      .sort((a, b) => a.t - b.t);

    const last = points.at(-1);
    if (!last) continue;

    const brand = brandOf(entry.provider);
    const labels: Record<string, string> = {
      five_hour: "5 hours",
      seven_day: "7 days",
      seven_day_opus: "7 days · Opus",
      seven_day_oauth_apps: "7 days · Apps",
      monthly: "30 days",
      primary: entry.label === "7 Tage" ? "7 days" : entry.label,
    };
    chosen.set(entry.provider, {
      rank: entryRank,
      series: {
        provider: entry.provider,
        short: brand.short,
        color: brand.series,
        label:
          language.value === "en"
            ? (labels[entry.window_key] ?? entry.label)
            : entry.label,
        points,
        last,
      },
    });
  }

  return [...chosen.values()].map((item) => item.series);
});

/** Dieselben Daten als Zeilen – Grundlage der Tabellenansicht. */
const tableRows = computed(() => {
  const columns = series.value;
  const stamps = [
    ...new Set(columns.flatMap((entry) => entry.points.map((p) => p.t))),
  ].sort((a, b) => a - b);
  return stamps.map((t) => ({
    t,
    values: columns.map(
      (entry) => entry.points.find((point) => point.t === t)?.used,
    ),
  }));
});

const domain = computed(() => {
  const end = chartNow.value.getTime();
  const start = end - props.hours * 3_600_000;
  return { start, end };
});

const scaleX = (t: number) => {
  const { start, end } = domain.value;
  const ratio = (t - start) / Math.max(1, end - start);
  return (
    PAD.left +
    Math.min(1, Math.max(0, ratio)) * (chartWidth.value - PAD.left - PAD.right)
  );
};

const scaleY = (used: number) => {
  const inner = HEIGHT.value - PAD.top - PAD.bottom;
  return PAD.top + (1 - Math.min(100, Math.max(0, used)) / 100) * inner;
};

/**
 * Snapshots sind Zustände, keine einzelnen Ereignisse. Deshalb bleibt jeder
 * Wert bis zum nächsten Snapshot konstant. Vor dem ersten gespeicherten
 * Messpunkt liegt die Linie bei 0 %; der letzte bekannte Zustand reicht bis
 * „Jetzt“.
 */
const pathOf = (entry: Series) => {
  const { start, end } = domain.value;
  const first = entry.points[0];
  if (!first) return "";

  let path = `M${scaleX(start).toFixed(1)} ${scaleY(0).toFixed(1)}`;
  for (const point of entry.points) {
    path += ` H${scaleX(point.t).toFixed(1)} V${scaleY(point.used).toFixed(1)}`;
  }
  return `${path} H${scaleX(end).toFixed(1)}`;
};

const gridValues = [0, 25, 50, 75, 100];

const timeTicks = computed(() => {
  const { start, end } = domain.value;
  const stepHours =
    props.hours <= 6 ? 2 : props.hours <= 24 ? 6 : props.hours <= 72 ? 12 : 24;
  const format = new Intl.DateTimeFormat(locale.value, {
    hour: "2-digit",
    minute: "2-digit",
    ...(props.hours > 48 ? { weekday: "short" } : {}),
  });

  // Nicht vom aktuellen Minutenwert rückwärts teilen: Aus 17:52 würden
  // sonst ausschließlich Ticks auf :52. Stattdessen an gut lesbaren vollen
  // Stunden ausrichten und den beweglichen rechten Rand als „Jetzt“ benennen.
  const first = new Date(start);
  first.setMinutes(0, 0, 0);
  if (stepHours === 24) first.setHours(0);
  else first.setHours(Math.ceil(first.getHours() / stepHours) * stepHours);
  while (first.getTime() < start) first.setHours(first.getHours() + stepHours);

  const ticks: Array<{ t: number; label: string }> = [];
  const cursor = new Date(first);
  while (cursor.getTime() <= end) {
    ticks.push({ t: cursor.getTime(), label: format.format(cursor) });
    cursor.setHours(cursor.getHours() + stepHours);
  }

  // Kein Zahlenlabel direkt neben „Jetzt“ quetschen.
  const last = ticks.at(-1);
  if (last && end - last.t < stepHours * 3_600_000 * 0.4) ticks.pop();
  ticks.push({ t: end, label: t("history.now") });
  return ticks;
});

// --- Crosshair: funktioniert mit Maus und Finger gleichermaßen -----------
const cursorT = ref<number>();

const onPointer = (event: PointerEvent) => {
  const bounds = (event.currentTarget as SVGElement).getBoundingClientRect();
  const x = event.clientX - bounds.left;
  const inner = chartWidth.value - PAD.left - PAD.right;
  const ratio = (x - PAD.left) / Math.max(1, inner);
  if (ratio < -0.05 || ratio > 1.05) {
    cursorT.value = undefined;
    return;
  }
  const { start, end } = domain.value;
  cursorT.value = start + Math.min(1, Math.max(0, ratio)) * (end - start);
};

const readout = computed(() => {
  if (cursorT.value === undefined) return undefined;
  const at = cursorT.value;

  const rows = series.value.map((entry) => {
    const first = entry.points[0] ?? entry.last;
    let nearest = at < first.t ? { t: at, used: 0 } : first;
    for (const point of entry.points) {
      if (point.t <= at) nearest = point;
      else break;
    }
    return { entry, point: nearest };
  });

  if (!rows.length) return undefined;
  return { x: scaleX(at), at, rows };
});

const timeFormat = computed(
  () =>
    new Intl.DateTimeFormat(locale.value, {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }),
);
</script>

<template>
  <section ref="wrapper" class="panel">
    <div class="panel-head">
      <div class="flex flex-row gap-2 items-center">
        <ChartLine class="size-6" :stroke-width="3" />
        <div>
          <h2 class="panel-title">{{ t("history.title") }}</h2>
          <p class="panel-sub">{{ t("history.subtitle") }}</p>
        </div>
      </div>

      <ul v-if="series.length" class="legend">
        <li v-for="entry in series" :key="entry.provider">
          <span class="swatch" :style="{ background: entry.color }" />
          {{ entry.short }} · {{ entry.label }}
        </li>
      </ul>
    </div>

    <div
      v-if="loading && !history"
      class="chart-placeholder"
      role="status"
      :aria-label="t('history.loading')"
    >
      <span v-for="index in 4" :key="index" class="placeholder-line" />
    </div>

    <!-- Auch ohne Punkte bleibt das Raster stehen: Der Verlauf ist ein fester
         Teil der Ansicht, kein Zustand, der kommt und geht. Die Kachel behält
         damit ihre Höhe, und der Hinweis erklärt die leere Fläche an Ort und
         Stelle. -->
    <div v-else ref="plot" class="plot">
      <svg
        class="chart"
        :width="chartWidth"
        :height="HEIGHT"
        :viewBox="`0 0 ${chartWidth} ${HEIGHT}`"
        role="img"
        :aria-label="t('history.aria')"
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
          <path
            :d="pathOf(entry)"
            fill="none"
            :stroke="entry.color"
            stroke-width="2"
            stroke-linejoin="round"
            stroke-linecap="round"
          />
          <circle
            :cx="scaleX(domain.end)"
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

      <p v-if="!series.length" class="chart-note">
        <Inbox class="size-4 shrink-0 opacity-80" aria-hidden="true" />
        {{ t("history.empty") }}
      </p>
    </div>

    <div v-if="readout" class="tooltip" :style="{ left: `${readout.x}px` }">
      <p class="tooltip-time">{{ timeFormat.format(new Date(readout.at)) }}</p>
      <p
        v-for="row in readout.rows"
        :key="row.entry.provider"
        class="tooltip-row"
      >
        <span class="swatch" :style="{ background: row.entry.color }" />
        {{ row.entry.short }}
        <strong>{{ Math.round(row.point.used) }} %</strong>
      </p>
    </div>

    <!-- Tabellenansicht derselben Daten für Screenreader und Export. -->
    <table v-if="series.length" class="sr-only">
      <caption>
        {{
          t("history.caption")
        }}
      </caption>
      <thead>
        <tr>
          <th>{{ t("history.time") }}</th>
          <th v-for="entry in series" :key="entry.provider">
            {{ entry.short }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in tableRows" :key="row.t">
          <td>{{ timeFormat.format(new Date(row.t)) }}</td>
          <td v-for="(value, index) in row.values" :key="index">
            {{ value === undefined ? "–" : `${Math.round(value)} %` }}
          </td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<style scoped>
.panel {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 0;
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

/* `flex: 1 1 0`: Die Höhe kommt ausschließlich aus dem freien Raum, nie aus
   dem Inhalt – sonst würde das gemessene SVG die Fläche aufschaukeln. */
.plot {
  position: relative;
  flex: 1 1 0;
  min-height: 4.5rem;
  margin-top: 0.4rem;
}

.chart {
  display: block;
}

/* Sitzt über der Zeichenfläche, nicht über den Zeitmarken darunter – deshalb
   endet der Kasten am unteren Rand des Rasters. */
.chart-note {
  position: absolute;
  inset: 0 0 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  color: #8f8f99;
  font-size: 0.6875rem;
  line-height: 1.5;
  padding-inline: 1.5rem;
  pointer-events: none;
  text-align: center;
  text-wrap: balance;
}

/* Nimmt dieselbe Fläche ein wie die Zeichenfläche danach – sonst springt die
   Kachel, sobald die ersten Punkte da sind. */
.chart-placeholder {
  position: relative;
  display: grid;
  align-content: space-evenly;
  flex: 1 1 0;
  min-height: 4.5rem;
  overflow: hidden;
  margin-top: 0.4rem;
}

.placeholder-line {
  display: block;
  width: 100%;
  height: 1px;
  background: rgb(255 255 255 / 7%);
}

.chart-placeholder::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent 10%,
    rgb(255 255 255 / 5%),
    transparent 70%
  );
  animation: chart-shimmer 1.4s ease-in-out infinite;
  transform: translateX(-100%);
}

@keyframes chart-shimmer {
  to {
    transform: translateX(100%);
  }
}
</style>
