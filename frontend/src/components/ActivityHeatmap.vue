<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from '@/composables/useI18n'
import type { ActivityCell } from '@/api/types'

const props = defineProps<{ cells: ActivityCell[]; compact: Intl.NumberFormat }>()

const { language, t } = useI18n()

const weekdays = computed(() =>
  language.value === 'en'
    ? ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    : ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'],
)
/** Nur jede zweite Zeile wird beschriftet – sieben Kürzel wären eine Wand. */
const LABELLED = [0, 2, 4, 6]
const HOUR_TICKS = [0, 6, 12, 18]

/**
 * Sequenzielle Rampe, ein Ton, hell → dunkel gegen die dunkle Fläche gedreht:
 * mehr Verbrauch ist heller. Absichtlich weder Koralle noch Türkis – das
 * Raster zeigt Menge über beide Anbieter hinweg, nicht Identität.
 * Geprüft gegen #16161a (monotone Lichtheit, ΔL ≥ 0.06, helles Ende 2,4:1).
 */
const RAMP = ['#454b9e', '#5a68c8', '#7488e6', '#94a9f7']
const EMPTY = 'rgb(255 255 255 / 6%)'

const byKey = computed(() => {
  const map = new Map<number, ActivityCell>()
  for (const cell of props.cells) map.set(cell.weekday * 24 + cell.hour, cell)
  return map
})

/**
 * Vierteilung über die belegten Zellen statt über den Höchstwert: Token je
 * Stunde streuen um Größenordnungen, eine lineare Teilung färbte fast alles
 * auf der untersten Stufe.
 */
const steps = computed(() => {
  const values = props.cells
    .map((cell) => cell.tokens)
    .filter((value) => value > 0)
    .sort((a, b) => a - b)
  if (!values.length) return []
  return [0.25, 0.5, 0.75].map(
    (quantile) => values[Math.floor((values.length - 1) * quantile)] ?? 0,
  )
})

const colorOf = (tokens: number) => {
  if (tokens <= 0) return EMPTY
  const level = steps.value.filter((step) => tokens > step).length
  return RAMP[level]
}

const rows = computed(() =>
  weekdays.value.map((label, weekday) => ({
    label,
    weekday,
    labelled: LABELLED.includes(weekday),
    cells: Array.from({ length: 24 }, (_, hour) => {
      const cell = byKey.value.get(weekday * 24 + hour)
      const tokens = cell?.tokens ?? 0
      return {
        hour,
        tokens,
        color: colorOf(tokens),
        title: cell
          ? t('heat.cell', {
              day: label,
              hour,
              messages: cell.messages,
              tokens: props.compact.format(tokens),
            })
          : t('heat.emptyCell', { day: label, hour }),
      }
    }),
  })),
)

const busiest = computed(() =>
  props.cells.reduce<ActivityCell | null>(
    (best, cell) => (!best || cell.messages > best.messages ? cell : best),
    null,
  ),
)

const summary = computed(() =>
  busiest.value
    ? t('heat.summary', {
        day: weekdays.value[busiest.value.weekday] ?? '',
        hour: busiest.value.hour,
      })
    : t('heat.emptySummary'),
)
</script>

<template>
  <figure class="heat">
    <figcaption class="head">
      <span class="title">{{ t('heat.title') }}</span>
      <span class="legend" aria-hidden="true">
        {{ t('heat.less') }}
        <i v-for="color in RAMP" :key="color" :style="{ background: color }" />
        {{ t('heat.more') }}
      </span>
    </figcaption>

    <div class="grid" role="img" :aria-label="summary">
      <template v-for="row in rows" :key="row.weekday">
        <span class="day" :class="{ shown: row.labelled }" aria-hidden="true">
          {{ row.labelled ? row.label : '' }}
        </span>
        <span
          v-for="cell in row.cells"
          :key="cell.hour"
          class="cell"
          :style="{ background: cell.color }"
          :title="cell.title"
        />
      </template>
    </div>

    <div class="axis" aria-hidden="true">
      <!-- Die Ticks sitzen auf derselben Spur wie die Zellen, sonst zeigt
           „12“ nicht auf die zwölfte Stunde. -->
      <span
        v-for="(hour, index) in HOUR_TICKS"
        :key="hour"
        class="tick"
        :style="{ gridColumn: `${2 + index * 6} / span 6` }"
      >
        {{ language === 'en' ? `${hour}:00` : `${hour} Uhr` }}
      </span>
    </div>
  </figure>
</template>

<style scoped>
.heat {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin: 0;
}

.head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.5rem;
}

.title {
  color: #f4f4f6;
  font-size: 0.75rem;
  font-weight: 800;
}

.legend {
  display: flex;
  align-items: center;
  gap: 2px;
  color: #9a9aa4;
  font-size: 0.5625rem;
}

.legend i {
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 2px;
}

.grid {
  display: grid;
  /* Feste Spur für die Wochentage, danach 24 gleich breite Stunden. */
  grid-template-columns: 1.1rem repeat(24, 1fr);
  /* 2 px Fläche als Trenner – kein Rahmen um die Zellen. */
  gap: 2px;
  align-items: center;
}

.day {
  color: #9a9aa4;
  font-size: 0.5625rem;
  font-variant-numeric: tabular-nums;
  line-height: 1;
  text-align: right;
  padding-right: 0.15rem;
}

.cell {
  aspect-ratio: 1;
  border-radius: 2px;
  min-height: 0.5rem;
}

.axis {
  display: grid;
  grid-template-columns: 1.1rem repeat(24, 1fr);
  gap: 2px;
  align-items: center;
  color: #9a9aa4;
  font-size: 0.5625rem;
}

.tick {
  font-variant-numeric: tabular-nums;
}
</style>
