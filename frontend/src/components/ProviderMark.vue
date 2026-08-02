<script setup lang="ts">
import claudeMark from '@/assets/logos/claude-mark.png'
import codexMark from '@/assets/logos/codex-mark.png'
import type { ProviderId } from '@/api/types'

const props = withDefaults(
  defineProps<{ provider: ProviderId; size?: number }>(),
  { size: 26 },
)

// Verkleinerte Fassungen der Originale aus `assets/logos`: Ein 5000-px-PNG
// belegt dekodiert rund 100 MB und ist auf einem Pi nicht vertretbar.
const SOURCES: Record<ProviderId, string> = {
  claude: claudeMark,
  codex: codexMark,
}
</script>

<template>
  <img
    :src="SOURCES[props.provider]"
    :width="size"
    :height="size"
    alt=""
    aria-hidden="true"
    decoding="async"
    draggable="false"
  />
</template>

<style scoped>
img {
  display: block;
  object-fit: contain;
  user-select: none;
}
</style>
