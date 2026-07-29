<script setup lang="ts">
import { computed } from 'vue'
import type { ServiceStatus } from '@/services/usage.types'

const props = defineProps<{
  status: ServiceStatus
}>()

const display = computed(() => {
  const states = {
    online: {
      label: 'Online',
      dot: 'bg-emerald-400',
      text: 'text-emerald-300',
      ring: 'ring-emerald-400/20',
    },
    degraded: {
      label: 'Eingeschränkt',
      dot: 'bg-amber-400',
      text: 'text-amber-300',
      ring: 'ring-amber-400/20',
    },
    outage: {
      label: 'Störung',
      dot: 'bg-rose-400',
      text: 'text-rose-300',
      ring: 'ring-rose-400/20',
    },
    unavailable: {
      label: 'Keine Daten',
      dot: 'bg-slate-500',
      text: 'text-slate-400',
      ring: 'ring-slate-500/20',
    },
  } as const

  return states[props.status]
})
</script>

<template>
  <span class="inline-flex items-center gap-1.5 text-xs font-medium" :class="display.text">
    <span
      class="size-1.5 rounded-full ring-4"
      :class="[display.dot, display.ring]"
      aria-hidden="true"
    />
    {{ display.label }}
  </span>
</template>
