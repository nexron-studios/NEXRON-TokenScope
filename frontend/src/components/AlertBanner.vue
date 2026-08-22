<script setup lang="ts">
import { useI18n } from '@/composables/useI18n'
import { RotateCw, TriangleAlert } from '@lucide/vue'

defineProps<{
  title: string
  hint?: string
  /** Solange ein Abruf läuft, bleibt der Knopf gesperrt. */
  busy?: boolean
}>()

defineEmits<{ retry: [] }>()

const { t } = useI18n()
</script>

<template>
  <div class="alert" role="alert">
    <span class="icon" aria-hidden="true">
      <TriangleAlert class="size-[1.15rem]" />
    </span>

    <div class="text">
      <p class="title">{{ title }}</p>
      <p v-if="hint" class="hint">{{ hint }}</p>
    </div>

    <button type="button" class="retry" :disabled="busy" @click="$emit('retry')">
      <RotateCw
        class="size-4 shrink-0"
        :class="{ 'animate-spin': busy }"
        aria-hidden="true"
      />
      {{ busy ? t('alert.checking') : t('alert.retry') }}
    </button>
  </div>
</template>

<style scoped>
.alert {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  border: 1px solid rgb(208 59 59 / 32%);
  border-radius: 1rem;
  background:
    linear-gradient(180deg, rgb(208 59 59 / 13%), rgb(208 59 59 / 7%)),
    #16161a;
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 5%);
  padding: 0.6rem 0.7rem 0.6rem 0.65rem;
}

.icon {
  display: grid;
  place-items: center;
  width: 2.25rem;
  height: 2.25rem;
  flex-shrink: 0;
  border: 1px solid rgb(208 59 59 / 30%);
  border-radius: 0.7rem;
  background: rgb(208 59 59 / 14%);
  color: #f29a95;
}

.text {
  min-width: 0;
  flex: 1;
}

.title {
  color: #fbe3e3;
  font-size: 0.8125rem;
  font-weight: 700;
  line-height: 1.25;
}

/* Der Zusatz sagt, was zu tun ist - er darf leiser sein als die Überschrift. */
.hint {
  margin-top: 0.1rem;
  overflow: hidden;
  color: #d2b8b8;
  font-size: 0.6875rem;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.retry {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  min-height: 2.25rem;
  flex-shrink: 0;
  border: 1px solid rgb(208 59 59 / 34%);
  border-radius: 0.7rem;
  background: rgb(208 59 59 / 12%);
  color: #f8c8c8;
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0 0.85rem;
  touch-action: manipulation;
  transition: background 140ms ease;
}

.retry:active {
  background: rgb(208 59 59 / 22%);
}

.retry:disabled {
  opacity: 0.55;
}
</style>
