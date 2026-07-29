<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  remaining?: number
  service: 'chatgpt' | 'claude'
}>()

const safeValue = computed(() =>
  typeof props.remaining === 'number'
    ? Math.min(100, Math.max(0, props.remaining))
    : 0,
)

const progressColor = computed(() => {
  if (safeValue.value <= 15) return 'from-rose-500 to-orange-400'
  if (safeValue.value <= 35) return 'from-amber-500 to-yellow-300'
  return props.service === 'chatgpt'
    ? 'from-emerald-500 to-mint-400'
    : 'from-violet-500 to-fuchsia-400'
})
</script>

<template>
  <div>
    <div
      class="h-2 overflow-hidden rounded-full bg-white/[0.065] ring-1 ring-white/[0.035]"
      role="progressbar"
      aria-label="Verbleibendes Kontingent"
      aria-valuemin="0"
      aria-valuemax="100"
      :aria-valuenow="remaining"
    >
      <div
        class="h-full rounded-full bg-gradient-to-r transition-[width] duration-700 ease-out"
        :class="progressColor"
        :style="{ width: `${safeValue}%` }"
      />
    </div>

    <div class="mt-2 flex justify-between text-[11px] text-slate-500">
      <span>{{ 100 - safeValue }} % genutzt</span>
      <span>{{ safeValue }} % verfügbar</span>
    </div>
  </div>
</template>
