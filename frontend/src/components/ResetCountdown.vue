<script setup lang="ts">
import { toRef } from 'vue'
import { useResetCountdown } from '@/composables/useResetCountdown'

const props = defineProps<{
  resetAt?: string
}>()

const { countdown, resetDate } = useResetCountdown(toRef(props, 'resetAt'))
</script>

<template>
  <div class="flex min-w-0 items-center gap-2.5">
    <div
      class="grid size-8 shrink-0 place-items-center rounded-lg bg-white/[0.045] text-slate-300"
      aria-hidden="true"
    >
      <svg viewBox="0 0 24 24" class="size-4" fill="none">
        <circle cx="12" cy="12" r="8.5" stroke="currentColor" stroke-width="1.7" />
        <path
          d="M12 7.5V12l3 2"
          stroke="currentColor"
          stroke-width="1.7"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
    </div>
    <div class="min-w-0">
      <p class="truncate text-xs font-semibold text-slate-50">{{ countdown }}</p>
      <p v-if="resetDate" class="mt-0.5 text-[11px] font-semibold text-slate-300">
        {{ resetDate }}
      </p>
    </div>
  </div>
</template>
