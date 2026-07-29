<script setup lang="ts">
import ServiceCard from '@/components/ServiceCard.vue'
import type { AIUsageService } from '@/services/usage.types'

defineProps<{
  services: AIUsageService[]
  compact: boolean
  loading: boolean
  refreshError?: string
  autoRefreshActive: boolean
}>()
</script>

<template>
  <main class="mt-7">
    <div
      v-if="refreshError"
      class="mb-4 rounded-xl border border-rose-400/15 bg-rose-400/[0.07] px-4 py-3 text-xs text-rose-200"
      role="alert"
    >
      {{ refreshError }}
    </div>

    <div
      v-if="services.length"
      class="grid gap-4 lg:grid-cols-2"
      :aria-busy="loading"
    >
      <ServiceCard
        v-for="service in services"
        :key="service.id"
        :service="service"
        :compact="compact"
      />
    </div>

    <div
      v-else-if="!loading"
      class="surface grid min-h-64 place-items-center rounded-2xl px-6 text-center"
    >
      <div>
        <p class="text-sm font-medium text-slate-300">Keine Dienste ausgewählt</p>
        <p class="mt-1 text-xs text-slate-500">
          Aktiviere ChatGPT oder Claude in den Einstellungen.
        </p>
      </div>
    </div>

    <div class="mt-4 flex flex-wrap items-center justify-between gap-x-4 gap-y-2 px-1">
      <p class="flex items-center gap-2 text-[10px] text-slate-600">
        <span
          class="size-1.5 rounded-full"
          :class="autoRefreshActive ? 'bg-emerald-500' : 'bg-slate-700'"
        />
        {{ autoRefreshActive ? 'Automatische Aktualisierung aktiv' : 'Automatische Aktualisierung pausiert' }}
      </p>
      <p class="text-[10px] text-slate-600">
        Usage lokal · Dienststatus über offizielle Statusseiten
      </p>
    </div>
  </main>
</template>
