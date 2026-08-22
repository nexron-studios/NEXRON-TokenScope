<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import ActivityHeatmap from "@/components/ActivityHeatmap.vue";
import TouchSegmented from "@/components/TouchSegmented.vue";
import { useLogSummary } from "@/composables/useHistory";
import { useSettings } from "@/composables/useSettings";
import { useI18n } from "@/composables/useI18n";
import { brandOf } from "@/theme/brands";
import { modelLabel } from "@/theme/models";
import type { LogGroupBy, TokenTotals } from "@/api/types";

const { settings } = useSettings();
const { language, locale, t } = useI18n();
const { summary, loading, error, load } = useLogSummary();

// Der Segmented Control arbeitet mit `string | number`; die Verengung auf
// LogGroupBy passiert beim Laden.
const groupBy = ref<string>("project");

const groups = computed<Array<{ value: LogGroupBy; label: string }>>(() => [
  { value: "project", label: t("logs.project") },
  { value: "model", label: t("logs.model") },
  { value: "day", label: t("logs.day") },
]);

const dayOptions = computed(() => [
  { value: 7, label: `7 ${t("unit.dayShort")}` },
  { value: 30, label: `30 ${t("unit.dayShort")}` },
  { value: 90, label: `90 ${t("unit.dayShort")}` },
]);

const reload = () =>
  void load(settings.value.logDays, groupBy.value as LogGroupBy);
onMounted(reload);
watch([groupBy, () => settings.value.logDays], reload);

const compact = computed(
  () =>
    new Intl.NumberFormat(locale.value, {
      notation: "compact",
      maximumFractionDigits: 1,
    }),
);
const decimal = computed(
  () => new Intl.NumberFormat(locale.value, { maximumFractionDigits: 1 }),
);

const totalOf = (totals: TokenTotals) =>
  totals.input_tokens +
  totals.output_tokens +
  totals.cache_write_tokens +
  totals.cache_read_tokens;

/** Balkenlänge relativ zur größten Gruppe – ein Vergleich, keine Skala. */
const maxTotal = computed(() =>
  Math.max(
    1,
    ...(summary.value?.buckets ?? []).map((bucket) => totalOf(bucket.totals)),
  ),
);

const insights = computed(() => summary.value?.insights);

/**
 * Acht Kennzahlen als Kachelreihe – acht Zahlen sind keine acht Balken wert.
 * `hint` erklärt, worauf sich die Zahl bezieht, ohne die Kachel zuzutexten.
 */
interface Tile {
  key: string;
  label: string;
  value: string;
  /** Rohwert, wo die Kachel einen aufbereiteten zeigt. */
  title?: string;
  hint?: string;
}

const tiles = computed<Tile[]>(() => {
  const data = insights.value;
  const days = summary.value?.days ?? settings.value.logDays;
  if (!data || !summary.value) return [];

  return [
    {
      key: "sessions",
      label: t("logs.sessions"),
      value: decimal.value.format(data.sessions),
    },
    {
      key: "messages",
      label: t("logs.messages"),
      value: decimal.value.format(data.messages),
    },
    {
      key: "tokens",
      label: t("logs.totalTokens"),
      value: compact.value.format(totalOf(summary.value.totals)),
      hint: t("logs.cacheIncluded"),
    },
    {
      key: "days",
      label: t("logs.activeDays"),
      value: decimal.value.format(data.active_days),
      hint: t("logs.ofDays", { days }),
    },
    {
      key: "streak",
      label: t("logs.currentStreak"),
      value: `${decimal.value.format(data.current_streak)} ${t("unit.dayShort")}`,
      hint: t("logs.daysInRow"),
    },
    {
      key: "longest",
      label: t("logs.longestStreak"),
      value: `${decimal.value.format(data.longest_streak)} ${t("unit.dayShort")}`,
      hint: t("logs.inRange"),
    },
    {
      key: "peak",
      label: t("logs.peakHour"),
      value: data.peak_hour === null ? "–" : `${data.peak_hour}:00`,
      hint: t("logs.mostMessages"),
    },
    {
      key: "model",
      label: t("logs.topModel"),
      value: data.top_model ? modelLabel(data.top_model, language.value) : "–",
      title: data.top_model ?? undefined,
      hint: data.top_model
        ? t("logs.messageShare", {
            percent: Math.round(
              (data.top_model_messages / Math.max(1, data.messages)) * 100,
            ),
          })
        : undefined,
    },
  ];
});

/**
 * Der Spaßvergleich am Fuß: Millionen Token sagen niemandem etwas, „zweimal
 * die Britannica“ schon. Die Werte sind grobe Schätzungen und als solche
 * ausgewiesen – es geht um die Größenordnung, nicht um die Nachkommastelle.
 */
interface Work {
  tokens: number;
  name: string;
}

const works = computed<Work[]>(() => [
  {
    tokens: 25_000,
    name: language.value === "en" ? "The Little Prince" : "Der kleine Prinz",
  },
  { tokens: 45_000, name: "Faust I" },
  {
    tokens: 120_000,
    name:
      language.value === "en"
        ? "Harry Potter and the Philosopher's Stone"
        : "Harry Potter und der Stein der Weisen",
  },
  { tokens: 290_000, name: "Moby-Dick" },
  {
    tokens: 750_000,
    name:
      language.value === "en" ? "The Lord of the Rings" : "Der Herr der Ringe",
  },
  {
    tokens: 1_000_000,
    name: language.value === "en" ? "the Bible" : "die Bibel",
  },
  {
    tokens: 1_500_000,
    name:
      language.value === "en"
        ? "the Harry Potter series"
        : "die Harry-Potter-Reihe",
  },
  {
    tokens: 60_000_000,
    name:
      language.value === "en"
        ? "Encyclopædia Britannica"
        : "die Encyclopædia Britannica",
  },
]);

/**
 * Drei abgeleitete Werte, die in keiner Kachel stehen: Sie brauchen den
 * Vergleich zweier Zahlen, und genau der geht in einer Kachelreihe unter.
 */
const facts = computed(() => {
  const data = insights.value;
  if (!data || !summary.value) return [];

  const total = totalOf(summary.value.totals);
  const perSession = data.sessions ? data.messages / data.sessions : 0;
  const perDay = data.active_days ? total / data.active_days : 0;
  const cacheShare = total
    ? (summary.value.totals.cache_read_tokens / total) * 100
    : 0;

  return [
    {
      key: "session",
      label: t("logs.messagesPerSession"),
      value: decimal.value.format(perSession),
    },
    {
      key: "day",
      label: t("logs.tokensPerDay"),
      value: compact.value.format(perDay),
    },
    {
      key: "cache",
      label: t("logs.fromCache"),
      value: `${Math.round(cacheShare)} %`,
    },
  ];
});

const comparison = computed(() => {
  const total = summary.value ? totalOf(summary.value.totals) : 0;
  if (total <= 0) return null;

  const work =
    [...works.value].reverse().find((entry) => total >= entry.tokens) ??
    works.value[0];
  if (!work) return null;
  const factor = total / work.tokens;
  return t("logs.comparison", {
    factor: decimal.value.format(factor),
    work: work.name,
  });
});
</script>

<template>
  <main class="view">
    <div class="controls">
      <TouchSegmented
        v-model="groupBy"
        :label="t('logs.grouping')"
        :options="groups"
      />
      <TouchSegmented
        v-model="settings.logDays"
        :label="t('logs.range')"
        :options="dayOptions"
      />
    </div>

    <!-- Acht Zahlen als Kachelreihe: acht Balken wären dieselbe Information
         mit mehr Farbe und weniger Ruhe. -->
    <ul v-if="insights" class="tiles">
      <li v-for="tile in tiles" :key="tile.key" class="tile">
        <p class="tile-label">{{ tile.label }}</p>
        <p class="tile-value" :title="tile.title">{{ tile.value }}</p>
        <p v-if="tile.hint" class="tile-hint">{{ tile.hint }}</p>
      </li>
    </ul>

    <!-- Ohne Kennzahlen (Ladezustand, Fehler) fällt die linke Spalte weg –
         sonst stünde die Liste in einer 23-rem-Rinne neben leerer Fläche. -->
    <div class="columns" :class="{ solo: !insights }">
      <section v-if="insights" class="panel rhythm">
        <ActivityHeatmap :cells="insights.activity" :compact="compact" />

        <dl class="facts">
          <div v-for="fact in facts" :key="fact.key">
            <dt>{{ fact.label }}</dt>
            <dd>{{ fact.value }}</dd>
          </div>
        </dl>

        <p
          v-if="comparison"
          class="comparison"
          :title="t('logs.comparisonTitle')"
        >
          {{ comparison }}
        </p>
      </section>

      <section class="panel">
        <header class="panel-head">
          <div>
            <h2 class="panel-title">{{ t("logs.title") }}</h2>
            <p class="panel-sub">{{ t("logs.subtitle") }}</p>
          </div>
          <p v-if="summary" class="meta">
            {{
              t("logs.files", {
                count: summary.scanned_files,
                tokens: compact.format(totalOf(summary.totals)),
              })
            }}
          </p>
        </header>

        <p v-if="error" class="state error">{{ error }}</p>
        <p v-else-if="loading && !summary" class="state">
          {{ t("logs.loading") }}
        </p>
        <p v-else-if="summary && !summary.buckets.length" class="state">
          {{ t("logs.empty") }}
        </p>

        <!-- Alle Gruppen, nicht nur die ersten paar: auf einem grossen Schirm
             ist der Platz da, und der Rest ist erscrollbar. -->
        <ul v-else-if="summary" class="rows pb-2">
          <li
            v-for="bucket in summary.buckets"
            :key="`${bucket.provider}-${bucket.key}`"
          >
            <div class="row-head">
              <span class="row-name" :title="bucket.label">
                <span
                  class="swatch"
                  :style="{ background: brandOf(bucket.provider).series }"
                />
                {{
                  summary.group_by === "model"
                    ? modelLabel(bucket.label, language).toLocaleUpperCase()
                    : bucket.label.toLocaleUpperCase()
                }}
              </span>
              <span class="row-value">{{
                compact.format(totalOf(bucket.totals))
              }}</span>
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
              {{
                t("logs.rowMeta", {
                  provider: brandOf(bucket.provider).short,
                  messages: bucket.messages,
                  cache: compact.format(bucket.totals.cache_read_tokens),
                })
              }}
            </p>
          </li>
        </ul>
      </section>
    </div>
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

/* Das Raster links in fester Breite, die Aufschlüsselung nimmt den Rest:
   Die Zellen sind quadratisch und wachsen nicht mit, die Balken profitieren
   von jedem Pixel mehr. */
.columns {
  display: grid;
  grid-template-columns: minmax(19rem, 23rem) 1fr;
  gap: 0.75rem;
  flex: 1;
  min-height: 0;
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

.columns.solo {
  grid-template-columns: 1fr;
}

.rhythm {
  gap: 0.55rem;
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
  font-weight: 700;
}

.panel-sub,
.meta {
  color: #b8b8c1;
  font-size: 0.6875rem;
}

.meta {
  flex-shrink: 0;
  font-variant-numeric: tabular-nums;
  text-align: right;
}

.tiles {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 0.45rem;
  flex-shrink: 0;
}

.tile {
  border: 1px solid rgb(255 255 255 / 7%);
  border-radius: 0.8rem;
  background: #16161a;
  padding: 0.35rem 0.6rem 0.4rem;
  min-width: 0;
}

.tile-label {
  color: #a8a8b2;
  font-size: 0.625rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tile-value {
  color: #f4f4f6;
  font-size: 1.05rem;
  font-weight: 800;
  line-height: 1.2;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tile-hint {
  color: #8f8f99;
  font-size: 0.5625rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.facts {
  display: grid;
  gap: 0.3rem;
  margin: 0;
}

.facts > div {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.5rem;
  border-top: 1px solid rgb(255 255 255 / 7%);
  padding-top: 0.3rem;
}

.facts dt {
  color: #a8a8b2;
  font-size: 0.6875rem;
}

.facts dd {
  margin: 0;
  color: #f4f4f6;
  font-size: 0.75rem;
  font-variant-numeric: tabular-nums;
}

.comparison {
  color: #9a9aa4;
  font-size: 0.625rem;
  line-height: 1.4;
  margin-top: auto;
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
  /* Die letzte sichtbare Zeile blendet aus, statt hart abgeschnitten zu
     werden – so ist zu sehen, dass darunter noch etwas kommt. */
  mask-image: linear-gradient(to bottom, #000 calc(100% - 1.4rem), transparent);
  /* Die Maske haengt am Element, nicht am Inhalt: Ohne diesen Auslauf bliebe
     der letzte Eintrag auch am Ende der Liste ausgeblendet. Der Wert
     entspricht der Hoehe des Verlaufs. */
  padding-bottom: 1.4rem;
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
  color: #f4f4f6;
  font-size: 0.8125rem;
  font-weight: 700;
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
  color: #f4f4f6;
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
  color: #b2b2bb;
  font-size: 0.6875rem;
}

.state {
  color: #bcbcc5;
  font-size: 0.8125rem;
  padding: 1.5rem 0;
  text-align: center;
}

.state.error {
  color: #f8c8c8;
}
</style>
