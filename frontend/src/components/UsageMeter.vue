<script setup lang="ts">
import { computed } from 'vue'
import { SEVERITY, severityOf } from '@/theme/brands'

const props = withDefaults(
  defineProps<{
    /** Verbleibendes Kontingent in Prozent. */
    remaining: number
    label: string
    /** Höhe der Spur; `lg` für das Hauptfenster einer Kachel. */
    size?: 'sm' | 'lg'
    /**
     * `inline` legt Bezeichnung, Spur und Wert in eine Zeile – spart in den
     * Nebenfenstern die Höhe, die auf 1024 × 600 fehlt.
     */
    variant?: 'stacked' | 'inline'
  }>(),
  { size: 'sm', variant: 'stacked' },
)

const value = computed(() => Math.min(100, Math.max(0, props.remaining)))
const severity = computed(() => severityOf(value.value))

/**
 * Im gesunden Zustand trägt die Füllung den Markenakzent, darunter
 * übernehmen die reservierten Statusfarben. Die Zustandsbezeichnung steht
 * immer daneben – die Farbe allein trägt nie die Bedeutung.
 */
const fill = computed(() =>
  severity.value === 'ok' ? 'var(--brand-accent)' : SEVERITY[severity.value].color,
)
</script>

<template>
  <div :class="variant === 'inline' ? 'inline-row' : undefined">
    <div v-if="variant === 'stacked'" class="flex items-baseline justify-between gap-3">
      <span class="meter-label">{{ label }}</span>
      <span class="meter-value">{{ Math.round(100 - value) }} % verbraucht</span>
    </div>
    <span v-else class="meter-label truncate">{{ label }}</span>

    <div
      class="meter-track"
      :class="[size === 'lg' ? 'h-3.5' : 'h-2', variant === 'inline' ? 'inline-track' : '']"
      role="meter"
      :aria-label="`${label}: ${Math.round(value)} Prozent verfügbar`"
      aria-valuemin="0"
      aria-valuemax="100"
      :aria-valuenow="Math.round(value)"
      :aria-valuetext="`${Math.round(value)} Prozent verfügbar, ${SEVERITY[severity].label}`"
    >
      <div class="meter-fill" :style="{ width: `${value}%`, background: fill }" />
    </div>

    <span v-if="variant === 'inline'" class="meter-value shrink-0">
      {{ Math.round(value) }} % frei
    </span>
  </div>
</template>

<style scoped>
.meter-label {
  color: var(--brand-ink-muted);
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.meter-value {
  color: var(--brand-ink-subtle);
  font-size: 0.6875rem;
  font-variant-numeric: tabular-nums;
}

.inline-row {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.inline-row .meter-label {
  flex-shrink: 0;
  min-width: 4.5rem;
}

.inline-track {
  flex: 1;
  margin-top: 0;
}

.meter-track {
  margin-top: 0.4rem;
  overflow: hidden;
  border-radius: 999px;
  /* Hellerer Schritt derselben Rampe: Der Zustand liest sich über die
     gesamte Breite, nicht nur im gefüllten Teil. */
  background: var(--brand-track);
}

.meter-fill {
  height: 100%;
  /* 4 px gerundetes Datenende, am Nullpunkt verankert. */
  border-radius: 0 4px 4px 0;
  transition: width 600ms cubic-bezier(0.22, 1, 0.36, 1), background 400ms ease;
}
</style>
