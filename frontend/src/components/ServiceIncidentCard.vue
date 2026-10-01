<script setup lang="ts">
import { computed } from 'vue'
import { ExternalLink } from '@lucide/vue'
import type { ProviderId, ServiceStatus } from '@/api/types'
import ProviderMark from '@/components/ProviderMark.vue'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { useI18n } from '@/composables/useI18n'

/** Nur Anbieter, die gerade wirklich gestört sind – siehe `isDisrupted`. */
const { statuses } = defineProps<{ statuses: ServiceStatus[] }>()

const { locale, t } = useI18n()

const PHASE_KEYS = {
  investigating: 'status.phase.investigating',
  identified: 'status.phase.identified',
  monitoring: 'status.phase.monitoring',
} as const

interface Row {
  key: string
  provider: ProviderId
  title: string
  /** Kurz genug, um nie gekürzt zu werden: Phase und Beginn. */
  detail: string
  /** Was nicht in die Zeile passt, steht im Tooltip. */
  tooltip: string
  url: string
}

const isSeveral = computed(() => rows.value.length > 1)

const isOutage = computed(() => statuses.some((status) => status.level === 'outage'))

const clockTime = (iso: string) =>
  new Intl.DateTimeFormat(locale.value, { hour: '2-digit', minute: '2-digit' }).format(
    new Date(iso),
  )

const phaseOf = (phase: string) =>
  phase in PHASE_KEYS ? t(PHASE_KEYS[phase as keyof typeof PHASE_KEYS]) : phase

const incidentRows = (status: ServiceStatus): Row[] =>
  status.incidents.map((incident) => {
    const detail = `${phaseOf(incident.status)} · ${t('status.since', { time: clockTime(incident.started_at) })}`
    const affects = incident.components.length
      ? t('status.affects', { components: incident.components.join(', ') })
      : ''
    return {
      key: incident.url,
      provider: status.provider,
      title: incident.name,
      detail,
      tooltip: [incident.name, detail, affects].filter(Boolean).join('. '),
      url: incident.url,
    }
  })

// Eine Komponente kann gestört sein, bevor jemand eine Meldung dazu schreibt.
// Dann ist sie das Einzige, was sich sagen lässt.
const componentRow = (status: ServiceStatus): Row => {
  const title = status.components
    .filter((component) => component.status !== 'operational')
    .map((component) => `${component.name}: ${t(`status.component.${component.status}`)}`)
    .join(' · ')
  return {
    key: `${status.provider}-components`,
    provider: status.provider,
    title,
    detail: '',
    tooltip: title,
    url: status.page_url,
  }
}

const rows = computed(() =>
  statuses.flatMap((status) =>
    status.incidents.length ? incidentRows(status) : [componentRow(status)],
  ),
)
</script>

<template>
  <section
    class="flex flex-col gap-1 rounded-2xl border py-1.5 pr-1.5 pl-2.5"
    :class="[
      isOutage
        ? 'border-[#d03b3b]/35 bg-[#d03b3b]/10 text-[#fbe3e3]'
        : 'border-[#fab219]/35 bg-[#fab219]/8 text-[#fbeccb]',
      { '[@media(max-height:44rem)]:flex-row [@media(max-height:44rem)]:gap-4': isSeveral },
    ]"
    role="alert"
    :aria-label="t('status.cardAria')"
  >
    <!-- Eine Zeile je Störung. Auf dem 600er-Panel ist jede Zeile Höhe, die
         den Kontingent-Kacheln fehlt. Der Titel gibt nach, Phase und Uhrzeit
         nie; was betroffen ist, steht im Tooltip.
         Sind mehrere Anbieter zugleich gestört, reicht auf niedrigen
         Bildschirmen selbst das nicht: Dann stehen die Störungen nebeneinander
         in einer Zeile, und Phase und Uhrzeit wandern in den Tooltip. Welcher
         Anbieter wie schwer betroffen ist, sagt die Kopfzeile ohnehin. -->
    <div
      v-for="row in rows"
      :key="row.key"
      class="flex min-h-8 min-w-0 items-center gap-2.5"
      :class="{ '[@media(max-height:44rem)]:flex-1': isSeveral }"
    >
      <!-- Der Tooltip hängt nur an der Meldung, nicht an der ganzen Zeile:
           Über dem Knopf daneben soll sein eigener stehen. -->
      <Tooltip>
        <TooltipTrigger as-child>
          <div class="flex min-w-0 flex-1 items-center gap-2.5" tabindex="0">
            <!-- Das Logo sagt, wessen Störung es ist – bei zwei Anbietern die
                 erste Frage, noch vor dem Titel. -->
            <ProviderMark class="shrink-0" :provider="row.provider" :size="18" />

            <p class="min-w-0 flex-1 truncate text-[0.8125rem] font-bold">{{ row.title }}</p>
            <p
              v-if="row.detail"
              class="shrink-0 text-[0.6875rem] font-semibold opacity-80"
              :class="{ '[@media(max-height:44rem)]:hidden': isSeveral }"
            >
              {{ row.detail }}
            </p>
          </div>
        </TooltipTrigger>
        <TooltipContent side="bottom" class="max-w-96">{{ row.tooltip }}</TooltipContent>
      </Tooltip>

      <Tooltip>
        <TooltipTrigger as-child>
          <a
            :href="row.url"
            target="_blank"
            rel="noopener"
            class="flex min-h-8 min-w-8 shrink-0 items-center justify-center gap-1.5 rounded-lg border border-current/25 px-2 text-xs font-bold opacity-85 [touch-action:manipulation] active:bg-white/5 xl:px-3"
          >
            <ExternalLink class="size-3.5" aria-hidden="true" />
            <span class="max-xl:sr-only">{{ t('status.page') }}</span>
          </a>
        </TooltipTrigger>
        <TooltipContent side="bottom">{{ t('status.page') }}</TooltipContent>
      </Tooltip>
    </div>
  </section>
</template>
