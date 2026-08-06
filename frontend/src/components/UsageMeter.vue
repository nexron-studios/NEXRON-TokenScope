<script setup lang="ts">
import { computed } from 'vue'
import { SEVERITY, severityOf } from '@/theme/brands'

const props = defineProps<{
  /** Verbleibendes Kontingent in Prozent. */
  remaining: number
  label: string
}>()

/**
 * Gefüllt heißt *verfügbar* – wie die große Zahl und die Kopfzeile der
 * Kachel. Die Beschriftung nennt deshalb ebenfalls den freien Anteil:
 * Sonst wächst der Balken in die eine Richtung und die Zahl daneben in die
 * andere.
 */
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
  <div class="meter">
    <div class="meter-head">
      <span class="meter-label">{{ label }}</span>
      <span class="meter-value">{{ Math.round(value) }} % frei</span>
    </div>

    <div
      class="meter-track"
      role="meter"
      :aria-label="`${label}: ${Math.round(value)} Prozent verfügbar`"
      aria-valuemin="0"
      aria-valuemax="100"
      :aria-valuenow="Math.round(value)"
      :aria-valuetext="`${Math.round(value)} Prozent verfügbar, ${SEVERITY[severity].label}`"
    >
      <div class="meter-fill" :style="{ width: `${value}%`, background: fill }" />
    </div>
  </div>
</template>

<style scoped>
/*
 * Jedes Limitfenster bekommt dieselbe Form: Beschriftung und Wert in einer
 * Zeile, darunter die Spur über die volle Kachelbreite. Gleiche Nullpunkte
 * und gleiche Länge – nur so lassen sich die Fenster untereinander
 * vergleichen.
 */
.meter-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
}

.meter-label {
  overflow: hidden;
  color: var(--brand-ink-muted);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.meter-value {
  flex-shrink: 0;
  color: var(--brand-ink-subtle);
  font-size: 0.6875rem;
  font-variant-numeric: tabular-nums;
}

.meter-track {
  overflow: hidden;
  height: 0.875rem;
  margin-top: 0.4rem;
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
