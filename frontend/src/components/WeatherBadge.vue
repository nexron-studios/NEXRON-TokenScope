<script setup lang="ts">
import { computed } from 'vue'
import {
  Cloud,
  CloudDrizzle,
  CloudFog,
  CloudHail,
  CloudLightning,
  CloudMoon,
  CloudRain,
  CloudSnow,
  CloudSun,
  Cloudy,
  Moon,
  Sun,
  ThermometerSnowflake,
  type LucideIcon,
} from '@lucide/vue'
import type { WeatherReport } from '@/api/types'
import { useI18n } from '@/composables/useI18n'
import { formatTemperature, isIcy, weatherKind } from '@/utils/weather'
import type { WeatherKind } from '@/utils/weather'

const { report } = defineProps<{ report: WeatherReport }>()

const { locale, t } = useI18n()

// Tagsüber Sonne, nachts Mond – bei allem, was von der Bewölkung abhängt.
// Regen sieht nachts nicht anders aus, deshalb steht dort nur ein Symbol.
const DAY_ICONS: Record<WeatherKind, LucideIcon> = {
  clear: Sun,
  'mostly-clear': CloudSun,
  cloudy: CloudSun,
  overcast: Cloudy,
  fog: CloudFog,
  drizzle: CloudDrizzle,
  rain: CloudRain,
  freezing: CloudHail,
  snow: CloudSnow,
  thunder: CloudLightning,
  hail: CloudHail,
}

const NIGHT_ICONS: Partial<Record<WeatherKind, LucideIcon>> = {
  clear: Moon,
  'mostly-clear': CloudMoon,
  cloudy: CloudMoon,
  overcast: Cloud,
}

const kind = computed(() => weatherKind(report.weather_code))

const icy = computed(() => isIcy(report.weather_code, report.temperature))

const icon = computed<LucideIcon>(() => {
  if (!report.is_day) {
    const night = NIGHT_ICONS[kind.value]
    if (night) return night
  }
  return DAY_ICONS[kind.value]
})

const temperature = computed(() =>
  formatTemperature(locale.value, report.temperature),
)

const condition = computed(() => t(`weather.${kind.value}`))

const hasRange = computed(
  () => report.day_high !== null && report.day_low !== null,
)

const high = computed(() =>
  report.day_high === null
    ? ''
    : formatTemperature(locale.value, report.day_high),
)

const low = computed(() =>
  report.day_low === null ? '' : formatTemperature(locale.value, report.day_low),
)

const range = computed(() =>
  hasRange.value
    ? t('weather.range', { high: high.value, low: low.value })
    : '',
)

// Der Titel trägt, was auf der Kopfzeile keinen Platz hat: Lage, Spanne und
// die gefühlte Temperatur.
const title = computed(() => {
  const lines = [condition.value, range.value]
  if (report.feels_like !== null) {
    lines.push(
      t('weather.feelsLike', {
        value: formatTemperature(locale.value, report.feels_like),
      }),
    )
  }
  if (icy.value) lines.push(t('weather.icy'))
  return lines.filter(Boolean).join(' · ')
})

const label = computed(() =>
  report.place
    ? t('weather.aria', {
        condition: condition.value,
        place: report.place,
        temperature: temperature.value,
      })
    : t('weather.ariaNoPlace', {
        condition: condition.value,
        temperature: temperature.value,
      }),
)
</script>

<template>
  <div
    class="flex min-w-0 items-center gap-2 text-[#c2c2ca]"
    :title="title"
    :aria-label="label"
  >
    <component
      :is="icon"
      class="size-5 shrink-0"
      :class="icy ? 'text-[#7cc7ff]' : 'text-[#9aa0ab]'"
      aria-hidden="true"
    />

    <span class="text-[1.05rem] font-bold tabular-nums text-white">
      {{ temperature }}
    </span>

    <span v-if="report.place" class="truncate text-xs font-bold">
      {{ report.place }}
    </span>

    <!-- Glätte ist der einzige Fall, in dem das Wetter zu einer Handlung
         führt. Farbe allein trüge das nicht, deshalb Symbol plus Text. -->
    <span
      v-if="icy"
      class="flex shrink-0 items-center gap-1 rounded-full border border-[#7cc7ff]/40 px-2 py-0.5 text-[0.625rem] font-extrabold tracking-wider text-[#7cc7ff] uppercase"
    >
      <ThermometerSnowflake class="size-3" aria-hidden="true" />
      {{ t('weather.icy') }}
    </span>

    <!-- Tageshoch und Tagestief. Sonne und Mond sagen das ohne Wort und
         ohne die Breite, die „Tagsüber … nachts …" bräuchte – ausgeschrieben
         steht es im Titel. -->
    <span
      v-else-if="hasRange"
      class="hidden shrink-0 items-center gap-1.5 text-xs font-bold text-[#8a8a94] tabular-nums xl:flex"
    >
      <Sun class="size-3.5 text-[#c9a227]" aria-hidden="true" />
      {{ high }}
      <Moon class="size-3.5 text-[#6f7684]" aria-hidden="true" />
      {{ low }}
    </span>
  </div>
</template>
