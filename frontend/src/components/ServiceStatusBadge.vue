<script setup lang="ts">
import { computed } from 'vue'
import type { ServiceLevel, ServiceStatus } from '@/api/types'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { useI18n } from '@/composables/useI18n'
import { isDisrupted, pageHost, SHORT_PROVIDER_NAMES } from '@/utils/serviceStatus'

const { status } = defineProps<{ status: ServiceStatus }>()

const { locale, t } = useI18n()

// Gleiche Farben wie der Dienst-Punkt daneben: grün heißt hier wie dort „läuft".
const LEVEL_COLOR: Record<ServiceLevel, string> = {
  ok: 'text-[#4f9d6d]',
  maintenance: 'text-[#7cc7ff]',
  degraded: 'text-[#fab219]',
  outage: 'text-[#f29a95]',
}

const clockTime = (iso: string) =>
  new Intl.DateTimeFormat(locale.value, { hour: '2-digit', minute: '2-digit' }).format(
    new Date(iso),
  )

const name = computed(() => SHORT_PROVIDER_NAMES[status.provider])

const label = computed(() =>
  status.stale
    ? t('status.unknown', { name: name.value })
    : t(`status.${status.level}`, { name: name.value }),
)

const color = computed(() => (status.stale ? 'text-[#8a8a94]' : LEVEL_COLOR[status.level]))

// Was neben „OK" noch wissenswert ist, aber keine Störung ist: eine anstehende
// Wartung oder eine eben behobene Störung. Nur eins davon, das Wichtigere.
const aside = computed(() => {
  if (status.stale || status.level !== 'ok') return ''
  const { maintenance, recently_resolved: resolved } = status
  if (maintenance?.status === 'in_progress') return t('status.maintenanceNow')
  if (maintenance) return t('status.maintenanceAt', { time: clockTime(maintenance.scheduled_for) })
  if (resolved?.resolved_at) return t('status.resolved', { time: clockTime(resolved.resolved_at) })
  return ''
})

// Was gestört ist: die Meldungen, oder – solange noch keiner eine geschrieben
// hat – die betroffenen Komponenten.
const issues = computed(() => {
  if (status.incidents.length) return status.incidents.map((incident) => incident.name).join(' · ')
  return status.components
    .filter((component) => component.status !== 'operational')
    .map((component) => component.name)
    .join(', ')
})

// Der Titel trägt, was auf schmalen Bildschirmen keinen Platz hat – auch den
// Zusatz, der dort ausgeblendet ist.
const title = computed(() => {
  const time = clockTime(status.fetched_at)
  const page = pageHost(status.page_url)
  if (status.stale) return t('status.staleTitle', { time })
  if (isDisrupted(status)) return t('status.disruptedTitle', { page, issues: issues.value, time })
  const base = t('status.okTitle', { page, time })
  return aside.value ? `${aside.value}. ${base}` : base
})
</script>

<template>
  <Tooltip>
    <TooltipTrigger as-child>
      <span
        class="flex shrink-0 items-center gap-1.5 text-xs font-bold whitespace-nowrap"
        :class="color"
        role="status"
        tabindex="0"
      >
        <!-- Hohler Kreis bei unbekanntem Stand: Farbe allein trüge den
             Unterschied zu „läuft" nicht. -->
        <span
          class="size-[0.45rem] shrink-0 rounded-full"
          :class="status.stale ? 'border border-current' : 'bg-current'"
          aria-hidden="true"
        />
        <span>{{ label }}</span>
        <!-- Der Zusatz ist nur Kontext. Schmal steht er im Titel, damit der
             Status selbst nie verdrängt wird. -->
        <span v-if="aside" class="font-semibold text-[#8a8a94] max-xl:hidden">{{ aside }}</span>
      </span>
    </TooltipTrigger>
    <TooltipContent side="bottom" class="max-w-80">{{ title }}</TooltipContent>
  </Tooltip>
</template>
