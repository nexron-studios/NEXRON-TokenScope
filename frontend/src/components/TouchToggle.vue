<script setup lang="ts">
const model = defineModel<boolean>({ required: true })

defineProps<{ label: string; hint?: string }>()
</script>

<template>
  <!-- Die ganze Zeile ist das Ziel: auf einem 7"-Panel trifft man keine
       11-px-Checkbox, aber immer eine 56 px hohe Zeile. -->
  <button
    type="button"
    class="row"
    role="switch"
    :aria-checked="model"
    @click="model = !model"
  >
    <span class="text">
      <span class="label">{{ label }}</span>
      <span v-if="hint" class="hint">{{ hint }}</span>
    </span>
    <span class="switch" :class="{ on: model }" aria-hidden="true">
      <span class="knob" />
    </span>
  </button>
</template>

<style scoped>
.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  width: 100%;
  min-height: 3.5rem;
  border: 1px solid rgb(255 255 255 / 8%);
  border-radius: 0.9rem;
  background: rgb(255 255 255 / 3%);
  color: inherit;
  padding: 0.55rem 0.9rem;
  text-align: left;
  touch-action: manipulation;
  transition: background 140ms ease, border-color 140ms ease;
}

.row:active {
  background: rgb(255 255 255 / 7%);
}

.text {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  min-width: 0;
}

.label {
  font-size: 0.875rem;
  font-weight: 700;
}

.hint {
  color: #bababf;
  font-size: 0.75rem;
  line-height: 1.25;
}

.switch {
  position: relative;
  flex-shrink: 0;
  width: 3.5rem;
  height: 2rem;
  border-radius: 999px;
  background: rgb(255 255 255 / 12%);
  transition: background 180ms ease;
}

.switch.on {
  background: #4c8f6f;
}

.knob {
  position: absolute;
  top: 0.25rem;
  left: 0.25rem;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 999px;
  background: #fff;
  transition: transform 180ms cubic-bezier(0.22, 1, 0.36, 1);
}

.switch.on .knob {
  transform: translateX(1.5rem);
}
</style>
