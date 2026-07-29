<script setup lang="ts">
import { computed } from 'vue'
import ResetCountdown from '@/components/ResetCountdown.vue'
import ServiceStatus from '@/components/ServiceStatus.vue'
import UsageProgress from '@/components/UsageProgress.vue'
import type { AIUsageService } from '@/services/usage.types'

const props = defineProps<{
  service: AIUsageService
  compact?: boolean
}>()

const hasUsage = computed(
  () => typeof props.service.remainingPercentage === 'number',
)

const source = computed(() => {
  const sources = {
    live: {
      label: 'Live',
      classes: 'border-emerald-400/20 bg-emerald-400/10 text-emerald-300',
    },
    extension: {
      label: 'Erweiterung',
      classes: 'border-sky-400/20 bg-sky-400/10 text-sky-300',
    },
    manual: {
      label: 'Manuell',
      classes: 'border-amber-400/20 bg-amber-400/10 text-amber-300',
    },
    mock: {
      label: 'Demo',
      classes: 'border-violet-400/20 bg-violet-400/10 text-violet-300',
    },
  } as const

  return sources[props.service.dataSource]
})

const updatedAt = computed(() =>
  new Intl.DateTimeFormat('de-DE', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(props.service.updatedAt)),
)
</script>

<template>
  <article
    class="surface relative overflow-hidden rounded-2xl"
    :class="compact ? 'p-4' : 'p-5 sm:p-6'"
  >
    <div
      class="pointer-events-none absolute -right-14 -top-20 size-44 rounded-full blur-3xl"
      :class="
        service.id === 'chatgpt' ? 'bg-emerald-500/[0.07]' : 'bg-violet-500/[0.08]'
      "
    />

    <div class="relative flex items-start justify-between gap-3">
      <div class="flex min-w-0 items-center gap-3">
        <div
          class="grid size-11 shrink-0 place-items-center rounded-xl border text-sm font-bold"
          :class="
            service.id === 'chatgpt'
              ? 'border-emerald-300/15 bg-emerald-300/[0.08] text-mint-400'
              : 'border-violet-300/15 bg-violet-300/[0.08] text-violet-300'
          "
          aria-hidden="true"
        >
          <svg v-if="service.id === 'chatgpt'" viewBox="0 0 24 24" class="size-6" fill="none">
            <path
              d="M12 3.2a4.2 4.2 0 0 1 4 3 4.2 4.2 0 0 1 2.7 6.5 4.2 4.2 0 0 1-4 5.7 4.2 4.2 0 0 1-6.7-.6 4.2 4.2 0 0 1-2.7-6.5 4.2 4.2 0 0 1 4-5.7A4.2 4.2 0 0 1 12 3.2Z"
              stroke="currentColor"
              stroke-width="1.6"
              stroke-linejoin="round"
            />
            <path d="m8.5 10 3.5-2 3.5 2v4L12 16l-3.5-2v-4Z" stroke="currentColor" stroke-width="1.4" />
          </svg>
          <span v-else class="font-serif text-xl font-medium">AI</span>
        </div>

        <div class="min-w-0">
          <h2 class="truncate text-base font-semibold tracking-tight">
            {{ service.name }}
          </h2>
          <p class="mt-0.5 truncate text-xs text-slate-500">
            {{ service.plan || 'Tarif nicht hinterlegt' }}
          </p>
        </div>
      </div>

      <div class="flex shrink-0 flex-col items-end gap-2">
        <ServiceStatus :status="service.status" />
        <span
          class="rounded-full border px-2 py-0.5 text-[9px] font-bold uppercase tracking-[0.12em]"
          :class="source.classes"
        >
          {{ source.label }}
        </span>
      </div>
    </div>

    <div v-if="hasUsage" class="relative" :class="compact ? 'mt-5' : 'mt-7'">
      <div class="flex items-end justify-between gap-4">
        <div>
          <p class="label">Verfügbar</p>
          <p class="mt-1 font-semibold tracking-[-0.05em] text-white" :class="compact ? 'text-4xl' : 'text-5xl'">
            {{ service.remainingPercentage }}<span class="ml-1 text-lg tracking-normal text-slate-500">%</span>
          </p>
        </div>
        <p v-if="service.usageText" class="mb-1 max-w-[45%] text-right text-[11px] leading-4 text-slate-500">
          {{ service.usageText }}
        </p>
      </div>

      <UsageProgress
        class="mt-4"
        :remaining="service.remainingPercentage"
        :service="service.id"
      />

      <div
        class="mt-5 grid grid-cols-[1fr_auto] items-center gap-3 border-t border-white/[0.07] pt-4"
      >
        <ResetCountdown :reset-at="service.resetAt" />
        <div class="text-right">
          <p class="label">Aktualisiert</p>
          <p class="mt-1 text-[11px] tabular-nums text-slate-400">{{ updatedAt }}</p>
        </div>
      </div>
    </div>

    <div v-else class="relative mt-6 rounded-xl border border-dashed border-white/10 bg-black/10 p-4">
      <div class="flex gap-3">
        <svg viewBox="0 0 24 24" class="mt-0.5 size-4 shrink-0 text-slate-500" fill="none">
          <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.7" />
          <path d="M12 11v5m0-8v.2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
        </svg>
        <div>
          <p class="text-xs font-medium text-slate-300">Keine Usage-Daten</p>
          <p class="mt-1 text-[11px] leading-4 text-slate-500">
            {{ service.error || 'Für diesen Dienst ist aktuell keine offizielle Usage-API verfügbar.' }}
          </p>
        </div>
      </div>
      <p class="mt-3 border-t border-white/[0.06] pt-3 text-[10px] text-slate-600">
        Zuletzt geprüft: {{ updatedAt }} Uhr
      </p>
    </div>
  </article>
</template>
