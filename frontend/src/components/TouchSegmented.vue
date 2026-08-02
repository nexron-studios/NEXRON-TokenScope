<script setup lang="ts">
interface Option<T> {
  value: T
  label: string
}

defineProps<{ label?: string; options: Option<number | string>[] }>()

const model = defineModel<number | string>({ required: true })
</script>

<template>
  <div>
    <p v-if="label" class="caption">{{ label }}</p>
    <!-- Segmentierte Auswahl statt <select>: Ein natives Dropdown ist auf
         einem kapazitiven 7"-Panel kaum treffsicher bedienbar. -->
    <div class="group" role="radiogroup" :aria-label="label">
      <button
        v-for="option in options"
        :key="String(option.value)"
        type="button"
        role="radio"
        :aria-checked="model === option.value"
        class="segment"
        :class="{ active: model === option.value }"
        @click="model = option.value"
      >
        {{ option.label }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.caption {
  margin-bottom: 0.4rem;
  color: #82828b;
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.group {
  display: flex;
  gap: 0.35rem;
  border: 1px solid rgb(255 255 255 / 8%);
  border-radius: 0.9rem;
  background: rgb(255 255 255 / 3%);
  padding: 0.3rem;
}

.segment {
  flex: 1;
  /* 48 px – die Untergrenze für ein kapazitives 7"-Panel. */
  min-height: 3rem;
  border: 0;
  border-radius: 0.65rem;
  background: transparent;
  color: #9a9aa3;
  font-size: 0.8125rem;
  font-weight: 600;
  touch-action: manipulation;
  transition: background 140ms ease, color 140ms ease;
}

.segment:active {
  background: rgb(255 255 255 / 6%);
}

.segment.active {
  background: rgb(255 255 255 / 12%);
  color: #fff;
}
</style>
