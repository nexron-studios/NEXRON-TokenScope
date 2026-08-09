<script setup lang="ts">
import { computed } from "vue";
import ProviderMark from "@/components/ProviderMark.vue";
import ProviderMascot from "@/components/ProviderMascot.vue";
import UsageMeter from "@/components/UsageMeter.vue";
import { useResetCountdown } from "@/composables/useResetCountdown";
import { brandOf, brandVars, SEVERITY, severityOf } from "@/theme/brands";
import type { ProviderUsage } from "@/api/types";

const props = defineProps<{
  provider: ProviderUsage;
  large?: boolean;
  /** Das Frontend erreicht sein Backend nicht – der Begleiter zeigt es mit. */
  backendDown?: boolean;
}>();

const brand = computed(() => brandOf(props.provider.id));
const vars = computed(() => brandVars(brand.value));

/** Das kürzeste Fenster ist im Alltag das relevante. */
const primary = computed(
  () =>
    props.provider.windows.find((window) => window.primary) ??
    props.provider.windows[0],
);
const secondary = computed(() =>
  props.provider.windows.filter((window) => window !== primary.value),
);

/**
 * Alle Fenster in einer Liste, das Hauptfenster zuerst – es steht als große
 * Zahl direkt darüber. Jedes Fenster bekommt dieselbe Spur, damit sich die
 * Längen vergleichen lassen; die Betonung des Hauptfensters trägt die Zahl.
 */
const meters = computed(() =>
  primary.value ? [primary.value, ...secondary.value] : [],
);

const severity = computed(() =>
  primary.value ? severityOf(primary.value.remaining_percent) : "ok",
);

/** Oberhalb der Hälfte neutral, darunter von Gold bis Rot zunehmend deutlich. */
const quotaStyle = computed((): Record<string, string> => {
  const remaining = Math.min(
    100,
    Math.max(0, primary.value?.remaining_percent ?? 0),
  );

  if (remaining > 50) return { color: "#ffffff", textShadow: "none" };

  const towardGold = remaining / 50;
  const red = Math.round(228 + (219 - 228) * towardGold);
  const green = Math.round(83 + (166 - 83) * towardGold);
  const blue = Math.round(83 + (59 - 83) * towardGold);
  const strength = 0.55 - towardGold * 0.2;

  return {
    color: `rgb(${red}, ${green}, ${blue})`,
    textShadow: `0 0 0.9rem rgba(${red}, ${green}, ${blue}, ${strength})`,
  };
});

const { countdown, resetDate } = useResetCountdown(
  () => primary.value?.resets_at,
);

const SOURCE_LABELS: Record<string, string> = {
  api: "Live-API",
  logs: "Aus CLI-Logs",
  cli: "codex-check",
  demo: "Demo",
  none: "Keine Quelle",
};

const STATUS_HINTS: Record<string, string> = {
  auth_missing: "Keine Anmeldedaten gefunden. Melde dich in der CLI an.",
  auth_expired: "Token abgelaufen – die CLI erneuert ihn beim nächsten Start.",
  unauthorized: "Token wurde abgelehnt. In der CLI neu anmelden.",
  rate_limited:
    "Anbieter drosselt gerade. Der Dienst versucht es später erneut.",
  unreachable: "Endpunkt nicht erreichbar.",
  unexpected_shape: "Antwortformat hat sich geändert.",
  disabled: "Anbieter ist im Backend deaktiviert.",
  error: "Unerwarteter Fehler.",
};

const updatedAt = computed(() =>
  new Intl.DateTimeFormat("de-DE", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(props.provider.fetched_at)),
);

/** Alter der angezeigten Werte in Minuten – nur bei Überbrückung relevant. */
const staleMinutes = computed(() => {
  if (!props.provider.stale) return 0;
  const age = Date.now() - new Date(props.provider.fetched_at).getTime();
  return Math.max(1, Math.round(age / 60_000));
});
</script>

<template>
  <article
    class="brand-card outline-2 outline-brand-accent/80"
    :class="brand.scheme"
    :style="vars"
  >
    <header class="flex items-start justify-between gap-3">
      <div class="flex min-w-0 items-center gap-3">
        <span class="mark"><ProviderMark :provider="provider.id" /></span>
        <div class="min-w-0">
          <h2 class="wordmark">{{ provider.name }}</h2>
          <p class="subline">
            {{ provider.plan ? `${provider.plan}-Tarif` : "Tarif unbekannt" }}
          </p>
        </div>
      </div>
      <span
        class="badge"
        :class="{
          'badge-demo': provider.source === 'demo',
          'badge-stale': provider.stale,
        }"
      >
        {{
          provider.stale
            ? "Gehalten"
            : (SOURCE_LABELS[provider.source] ?? provider.source)
        }}
      </span>
    </header>

    <div v-if="primary" class="body">
      <div class="flex items-end justify-between gap-4">
        <div>
          <p class="eyebrow-row">
            <span class="eyebrow">Verfügbar · {{ primary.label }}</span>
            <!-- Zustand steht neben der Bezeichnung: Symbol und Wort tragen
                 die Bedeutung, die Farbe verstärkt sie nur. -->
            <span
              class="state"
              :style="{
                color: severity === 'ok' ? undefined : SEVERITY[severity].color,
              }"
            >
              <svg viewBox="0 0 16 16" class="state-icon" aria-hidden="true">
                <circle
                  v-if="severity === 'ok'"
                  cx="8"
                  cy="8"
                  r="4.2"
                  fill="currentColor"
                />
                <path
                  v-else-if="severity === 'warning'"
                  d="M8 2.4 15 14H1L8 2.4Z"
                  fill="currentColor"
                />
                <path
                  v-else
                  d="M8 1.6 14.4 8 8 14.4 1.6 8 8 1.6Z"
                  fill="currentColor"
                />
              </svg>
              {{ SEVERITY[severity].label }}
            </span>
          </p>
          <p class="figure" :class="{ 'figure-lg': large }" :style="quotaStyle">
            {{ Math.round(primary.remaining_percent)
            }}<span class="unit">%</span>
          </p>
        </div>

        <div class="text-right">
          <p class="eyebrow">Reset</p>
          <p class="countdown">{{ countdown }}</p>
          <p v-if="resetDate" class="footnote">{{ resetDate }} Uhr</p>
        </div>
      </div>

      <div class="body-row">
        <div class="meters">
          <UsageMeter
            v-for="window in meters"
            :key="window.key"
            :remaining="window.remaining_percent"
            :label="window.label"
          />
        </div>

        <ProviderMascot :provider="provider" :backend-down="backendDown" />
      </div>
    </div>

    <!-- Ohne Zahlen trägt der Begleiter die Fläche: Er füllt den Raum, den
         sonst Meter und Countdown einnehmen, und zeigt dieselbe Störung, die
         darunter im Klartext steht. -->
    <div v-else class="empty">
      <div class="empty-stage">
        <ProviderMascot :provider="provider" :backend-down="backendDown" />
      </div>
      <div class="empty-copy">
        <p class="empty-title">Keine Kontingentdaten</p>
        <p class="empty-text">
          {{
            provider.message ||
            STATUS_HINTS[provider.status] ||
            "Quelle liefert nichts."
          }}
        </p>
      </div>
    </div>

    <footer class="foot">
      <span>Stand {{ updatedAt }} Uhr</span>
      <!-- Das Alter steht schon links im "Stand …" – hier zählt der Grund. -->
      <span
        v-if="provider.stale"
        class="foot-note"
        :title="`Vor ${staleMinutes} Min. geholt · ${provider.warning ?? 'Abruf gescheitert'}`"
      >
        {{ provider.warning || "Wert wird gehalten" }}
      </span>
      <span v-else-if="provider.source === 'logs'" class="foot-note">
        Wert stammt aus der letzten CLI-Sitzung
      </span>
    </footer>
  </article>
</template>

<style scoped>
.brand-card {
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  /* Neutral: Die Markenfarbe trägt die `outline-brand-accent` am Element.
     Diese Linie bleibt die innere Kante der Fläche. */
  border: 1px solid var(--brand-hairline);
  border-radius: 1.25rem;
  background: var(--brand-surface);
  color: var(--brand-ink);
  padding: 0.95rem 1.1rem 0.75rem;
}

.brand-card > header {
  flex-shrink: 0;
}

/* Der Rumpf nimmt den freien Raum ein und wächst nach unten. Kein
   `center`: Bei zwei Limitfenstern würde die Kachel sonst oben wie unten
   überlaufen und Kopf- wie Fußzeile überdecken. */
.body {
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* Der weiche Auslauf hinter der Outline. Reichweiten bleiben knapp: Die Shell
   gibt den Kacheln nur 0.7–0.9rem Padding, alles darüber schneidet ihr
   `overflow: hidden` weg – ein weiter Schatten wäre dort nicht dezent,
   sondern schlicht unsichtbar. */
.brand-card {
  /* 1. Lichtkante oben innen – setzt die Fläche von der Outline ab.
     2. Schein in der Markenfarbe – läuft hinter der Outline weich aus.
     3. Kontaktschatten nach unten – gibt der Kachel Höhe über dem Grund. */
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 6%),
    0 0 0.9rem -0.25rem color-mix(in srgb, var(--brand-accent) 55%, transparent),
    0 6px 14px rgb(0 0 0 / 55%);
}

.mark {
  display: grid;
  place-items: center;
  width: 2.5rem;
  height: 2.5rem;
  flex-shrink: 0;
  border: 1px solid var(--brand-hairline);
  border-radius: 0.8rem;
  background: var(--brand-surface-raised);
}

.wordmark {
  font-family: var(--brand-display);
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  line-height: 1.2;
}

.subline {
  margin-top: 0.1rem;
  color: var(--brand-ink-muted);
  font-size: 0.75rem;
}

.badge {
  flex-shrink: 0;
  border: 1px solid var(--brand-hairline);
  border-radius: 999px;
  color: var(--brand-ink-muted);
  font-size: 0.625rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  padding: 0.25rem 0.55rem;
  text-transform: uppercase;
}

.badge-demo {
  border-color: color-mix(in srgb, var(--brand-accent) 45%, transparent);
  color: var(--brand-accent);
}

/* Überbrückte Werte: erkennbar, aber nicht alarmierend – sie stimmen ja noch. */
.badge-stale {
  border-color: rgb(250 178 25 / 55%);
  color: #fab219;
}

.foot-note {
  max-width: 62%;
  overflow: hidden;
  text-align: right;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.eyebrow {
  color: var(--brand-ink-subtle);
  font-size: 0.625rem;
  font-weight: 800;
  letter-spacing: 0.11em;
  text-transform: uppercase;
}

.figure {
  margin-top: 0.05rem;
  font-size: 2.9rem;
  font-variant-numeric: tabular-nums;
  font-weight: 700;
  letter-spacing: -0.045em;
  line-height: 1;
  transition:
    color 220ms ease,
    text-shadow 220ms ease;
}

.figure-lg {
  font-size: 3.4rem;
}

.unit {
  margin-left: 0.15rem;
  color: inherit;
  font-size: 1.15rem;
  font-weight: 700;
  letter-spacing: 0;
  opacity: 0.72;
}

.countdown {
  margin-top: 0.15rem;
  font-size: 1.05rem;
  font-variant-numeric: tabular-nums;
  font-weight: 700;
}

.footnote,
.foot {
  color: var(--brand-ink-subtle);
  font-size: 0.6875rem;
}

.eyebrow-row {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.state {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  color: var(--brand-ink-muted);
  font-size: 0.6875rem;
  font-weight: 800;
}

.state-icon {
  width: 0.7rem;
  height: 0.7rem;
}

/* Balken und Begleiter teilen sich eine Zeile: Die Meterspalte ist bei zwei
   Fenstern ohnehin höher als er, damit kostet er keine zusätzliche Höhe. */
.body-row {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  margin-top: 0.85rem;
}

/* Alle Limitfenster untereinander, gleiche Breite, gleicher Nullpunkt. */
.meters {
  display: grid;
  flex: 1;
  gap: 0.7rem;
  min-width: 0;
}

/* Nimmt denselben Raum ein wie der Rumpf mit Zahlen – die Kachel behält
   ihre Höhe, egal ob eine Quelle liefert oder nicht. */
.empty {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.6rem;
  min-height: 0;
  overflow: hidden;
  border: 1px dashed var(--brand-hairline);
  border-radius: 0.9rem;
  padding: 0.8rem 0.9rem;
  text-align: center;
}

/* Die Bühne nimmt die freie Höhe und hält die Figur in ihrer Mitte. Ohne
   Begleiter – abgeschaltete Bewegung, kein hinterlegter Clip – fällt sie in
   sich zusammen, damit der Text nicht allein am unteren Rand steht. */
/* Wächst in die freie Höhe hinein, gibt sie aber auch wieder her: Die
   Startgröße bleibt klein und `min-height: 0` erlaubt das Schrumpfen. So
   diktiert der leere Zustand der Kachelzeile keine neue Höhe, sondern
   füllt die, die der Nachbar ohnehin vorgibt. */
.empty-stage {
  position: relative;
  display: grid;
  place-items: center;
  flex: 1 1 4rem;
  width: 100%;
  min-height: 0;
  --mascot-size: 8rem;
}

.empty-stage:empty {
  flex: none;
}

/* Weicher Schein in der Markenfarbe: hebt die Figur von der Fläche ab,
   ohne eine zweite Kante zu ziehen. */
.empty-stage::before {
  content: "";
  position: absolute;
  width: min(11rem, 100%);
  aspect-ratio: 1;
  border-radius: 50%;
  background: radial-gradient(
    circle,
    color-mix(in srgb, var(--brand-accent) 18%, transparent),
    transparent 68%
  );
}

.empty-stage:empty::before {
  display: none;
}

.empty-copy {
  flex-shrink: 0;
  max-width: 22rem;
}

.empty-title {
  font-size: 0.875rem;
  font-weight: 700;
}

.empty-text {
  margin-top: 0.25rem;
  color: var(--brand-ink-muted);
  font-size: 0.75rem;
  line-height: 1.35;
  text-wrap: balance;
}

.foot {
  display: flex;
  flex-shrink: 0;
  justify-content: space-between;
  gap: 0.75rem;
  border-top: 1px solid var(--brand-hairline);
  padding-top: 0.5rem;
}
</style>
