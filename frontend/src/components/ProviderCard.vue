<script setup lang="ts">
import { computed } from "vue";
import { useNow } from "@vueuse/core";
import ProviderMark from "@/components/ProviderMark.vue";
import ProviderMascot from "@/components/ProviderMascot.vue";
import UsageMeter from "@/components/UsageMeter.vue";
import { useResetCountdown } from "@/composables/useResetCountdown";
import { useI18n } from "@/composables/useI18n";
import {
  brandOf,
  brandVars,
  SEVERITY,
  severityOf,
  type Severity,
} from "@/theme/brands";
import type { ProviderUsage, UsageWindow } from "@/api/types";
import {
  CircleCheck,
  ClockFading,
  OctagonAlert,
  ScrollText,
  Timer,
  TriangleAlert,
  type LucideIcon,
} from "@lucide/vue";

const props = defineProps<{
  provider: ProviderUsage;
  /** Das Frontend erreicht sein Backend nicht – der Begleiter zeigt es mit. */
  backendDown?: boolean;
}>();

const { language, locale, t } = useI18n();
const clock = useNow({ interval: 60_000 });

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

const { countdown, resetDate, isDue } = useResetCountdown(
  () => primary.value?.resets_at,
);

const sourceLabel = computed(() =>
  t(`provider.source.${props.provider.source}`),
);

const statusHint = computed(() =>
  props.provider.status === "ok"
    ? undefined
    : t(`provider.error.${props.provider.status}`),
);

// Bei gehaltenen Werten steht in `status` noch der letzte gute Abruf – der
// Grund für den Aussetzer hängt an `warning_status`.
const warningHint = computed(() => {
  const reason = props.provider.warning_status;
  if (!reason || reason === "ok") return undefined;
  return t(`provider.error.${reason}`);
});

const emptyMessage = computed(
  () => statusHint.value || t("provider.noData"),
);

const severityLabel = computed(() => t(`provider.status.${severity.value}`));

const SEVERITY_ICON: Record<Severity, LucideIcon> = {
  ok: CircleCheck,
  warning: TriangleAlert,
  critical: OctagonAlert,
};

// Bei gehaltenen Werten sagt das Symbol das Alter, nicht den Füllstand.
const stateIcon = computed<LucideIcon>(() =>
  props.provider.stale ? ClockFading : SEVERITY_ICON[severity.value],
);

const windowLabel = (window: UsageWindow): string => {
  if (language.value === "de") return window.label;

  const known: Record<string, string> = {
    five_hour: "5 hours",
    seven_day: "7 days",
    seven_day_opus: "7 days · Opus",
    seven_day_oauth_apps: "7 days · Apps",
    monthly: "30 days",
  };
  const knownLabel = known[window.key];
  if (knownLabel !== undefined) return knownLabel;

  const minutes = window.window_minutes;
  if (!minutes) return window.label;
  if (minutes % 1440 === 0) {
    const days = minutes / 1440;
    return `${days} ${days === 1 ? "day" : "days"}`;
  }
  if (minutes % 60 === 0) {
    const hours = minutes / 60;
    return `${hours} ${hours === 1 ? "hour" : "hours"}`;
  }
  return `${minutes} minutes`;
};

const updatedAt = computed(() =>
  new Intl.DateTimeFormat(locale.value, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(props.provider.fetched_at)),
);

/** Laufende relative Angabe: "vor 12 Min.", "vor 2 Std." oder "vor 3 Tagen". */
const updatedRelative = computed(() => {
  const fetchedAt = new Date(props.provider.fetched_at).getTime();
  const ageMinutes = Math.max(0, (clock.value.getTime() - fetchedAt) / 60_000);
  const formatter = new Intl.RelativeTimeFormat(locale.value, {
    numeric: "auto",
  });

  if (ageMinutes < 1) return t("provider.justNow");
  if (ageMinutes < 60) {
    return formatter.format(-Math.round(ageMinutes), "minute");
  }
  if (ageMinutes < 1_440) {
    return formatter.format(-Math.round(ageMinutes / 60), "hour");
  }
  return formatter.format(-Math.round(ageMinutes / 1_440), "day");
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
            {{
              provider.plan
                ? t("provider.plan", { plan: provider.plan })
                : t("provider.planUnknown")
            }}
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
        {{ provider.stale ? t("provider.held") : sourceLabel }}
      </span>
    </header>

    <div v-if="primary" class="body">
      <div class="flex items-end justify-between gap-4">
        <div class="min-w-0">
          <p class="eyebrow-row">
            <span class="eyebrow">{{
              t(provider.stale ? "provider.lastKnown" : "provider.available", {
                label: windowLabel(primary),
              })
            }}</span>
            <!-- Zustand steht neben der Bezeichnung: Symbol und Wort tragen
                 die Bedeutung, die Farbe verstärkt sie nur. -->
            <span
              class="state"
              :style="{
                color: severity === 'ok' ? undefined : SEVERITY[severity].color,
              }"
            >
              <component
                :is="stateIcon"
                class="size-[0.85rem] shrink-0"
                :stroke-width="2.4"
                aria-hidden="true"
              />
              {{ provider.stale ? t("provider.status.stale") : severityLabel }}
            </span>
          </p>
          <p class="figure" :style="quotaStyle">
            {{ Math.round(primary.remaining_percent)
            }}<span class="unit">%</span>
          </p>
        </div>

        <div class="shrink-0 text-right">
          <p class="eyebrow inline-flex items-center gap-1.5">
            <Timer
              class="size-[0.8rem] shrink-0"
              :stroke-width="2.4"
              aria-hidden="true"
            />
            {{
              t(
                provider.stale && isDue
                  ? "provider.resetWas"
                  : "provider.reset",
              )
            }}
          </p>
          <!-- „bereits erfolgt“ ist ein Satz, keine Uhrzeit: In der Größe der
               Countdown-Ziffern verdrängte er die Zeile links. -->
          <p
            class="countdown"
            :class="{ 'countdown-word': provider.stale && isDue }"
          >
            {{ provider.stale && isDue ? t("provider.expired") : countdown }}
          </p>
          <p v-if="resetDate" class="footnote">{{ resetDate }}</p>
        </div>
      </div>

      <div class="body-row">
        <div class="meters">
          <UsageMeter
            v-for="window in meters"
            :key="window.key"
            :remaining="window.remaining_percent"
            :label="windowLabel(window)"
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
        <ProviderMascot
          :provider="provider"
          :backend-down="backendDown"
          :force-clip="
            provider.id === 'codex' ? 'cloudling-error.mp4' : 'clawd-error.mp4'
          "
        />
      </div>
      <div class="empty-copy">
        <p class="empty-title">{{ t("provider.noQuota") }}</p>
        <p class="empty-text">{{ emptyMessage }}</p>
      </div>
    </div>

    <footer class="foot">
      <span :title="t('provider.updatedExact', { time: updatedAt })">
        {{ t("provider.updatedAgo", { relative: updatedRelative }) }}
      </span>
      <!-- Das Alter steht schon links – hier zählt der Grund. -->
      <span
        v-if="provider.stale"
        class="foot-note"
        :title="
          t('provider.staleTitle', {
            relative: updatedRelative,
            reason: warningHint || statusHint || t('provider.fetchFailed'),
          })
        "
      >
        <component
          :is="warningHint ? TriangleAlert : ClockFading"
          class="size-3 shrink-0"
          :stroke-width="2.2"
          aria-hidden="true"
        />
        <span class="truncate">{{
          warningHint || statusHint || t("provider.valueHeld")
        }}</span>
      </span>
      <span v-else-if="provider.source === 'logs'" class="foot-note">
        <ScrollText
          class="size-3 shrink-0"
          :stroke-width="2.2"
          aria-hidden="true"
        />
        <span class="truncate">{{ t("provider.fromLogs") }}</span>
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

/* Alte Werte bleiben sichtbar, müssen aber eindeutig als Altstand erkennbar sein. */
.badge-stale {
  border-color: rgb(250 178 25 / 55%);
  color: #fab219;
}

.foot-note {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  max-width: 62%;
  min-width: 0;
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
  white-space: nowrap;
}

.countdown-word {
  font-size: 0.8125rem;
  line-height: 1.3;
}

.footnote,
.foot {
  color: var(--brand-ink-subtle);
  font-size: 0.6875rem;
}

/* Wird es eng, rutscht der Zustand als Ganzes in die zweite Zeile – lieber
   das, als dass beide Angaben mitten im Wort brechen. */
.eyebrow-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.1rem 0.55rem;
}

.state {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  color: var(--brand-ink-muted);
  font-size: 0.6875rem;
  font-weight: 800;
  white-space: nowrap;
}

/* Balken und Begleiter teilen sich eine Zeile: Die Meterspalte ist bei zwei
   Fenstern ohnehin höher als er, damit kostet er keine zusätzliche Höhe. */
/* Die Zeile nimmt die verbleibende Höhe des Rumpfs – erst dadurch ist sie für
   den Begleiter eine feste Bezugsgröße, an der sein `max-height` greift.
   Vorher hatte sie nur Inhaltshöhe, der Begleiter behielt seine 5.5rem und
   lief auf dem 600px-Panel unten aus der Kachel heraus, wo `overflow: hidden`
   ihn abschnitt. Das Polster darunter hält ihn zusätzlich von der Fußlinie
   weg. */
.body-row {
  display: flex;
  /* Oben verankert wie der übrige Rumpf. Zentriert verteilte die Zeile ihren
     Überlauf auf beide Seiten – die Meterbeschriftung lief dann in die
     Prozentzahl darüber – und schob bei nur einem Limitfenster den Balken
     grundlos in die Mitte der freien Fläche. */
  align-items: flex-start;
  flex: 1;
  gap: 0.9rem;
  min-height: 0;
  margin-top: 0.85rem;
  padding-bottom: 0.35rem;
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
  position: relative;
  display: grid;
  grid-template-columns: minmax(5.75rem, 7.25rem) minmax(0, 1fr);
  flex: 1;
  align-items: center;
  gap: 1rem;
  min-height: 0;
  overflow: hidden;
  border: 1px solid
    color-mix(in srgb, var(--brand-accent) 24%, var(--brand-hairline));
  border-radius: 0.9rem;
  background:
    linear-gradient(
      115deg,
      color-mix(in srgb, var(--brand-accent) 9%, transparent),
      transparent 48%
    ),
    rgb(255 255 255 / 1.5%);
  padding: 0.75rem 1rem;
  text-align: left;
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
  align-self: stretch;
  width: 100%;
  min-height: 0;
  overflow: hidden;
  --mascot-size: 7rem;
}

.empty-stage:empty {
  display: none;
}

.empty-stage:empty + .empty-copy {
  grid-column: 1 / -1;
  justify-self: center;
  text-align: center;
}

/* Weicher Schein in der Markenfarbe: hebt die Figur von der Fläche ab,
   ohne eine zweite Kante zu ziehen. */
.empty-stage::before {
  content: "";
  position: absolute;
  width: min(9rem, 130%);
  aspect-ratio: 1;
  border-radius: 50%;
  background: radial-gradient(
    circle,
    color-mix(in srgb, var(--brand-accent) 22%, transparent),
    transparent 68%
  );
}

.empty-stage:empty::before {
  display: none;
}

.empty-copy {
  position: relative;
  z-index: 1;
  min-width: 0;
  max-width: 28rem;
}

.empty-title {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 0.875rem;
  font-weight: 800;
  line-height: 1.2;
}

.empty-title::before {
  content: "";
  width: 0.45rem;
  height: 0.45rem;
  flex: none;
  border-radius: 999px;
  background: var(--brand-accent);
  box-shadow: 0 0 0.65rem
    color-mix(in srgb, var(--brand-accent) 70%, transparent);
}

.empty-text {
  margin-top: 0.35rem;
  color: var(--brand-ink-muted);
  font-size: 0.75rem;
  line-height: 1.45;
  text-wrap: pretty;
}

.foot {
  display: flex;
  flex-shrink: 0;
  justify-content: space-between;
  gap: 0.75rem;
  border-top: 1px solid var(--brand-hairline);
  padding-top: 0.5rem;
}

/* Steht ein Banner über den Kacheln oder ist das Panel ohnehin niedrig, fehlen
   dem Rumpf schnell 30 bis 50 Pixel. Dann geben zuerst die Abstände nach und
   die Prozentzahl gibt etwas Größe ab – beides kostet keine Aussage, während
   ein abgeschnittenes zweites Limitfenster eine ganze Zeile verschluckt. */
@media (max-height: 640px) {
  .brand-card {
    gap: 0.5rem;
    padding: 0.7rem 0.9rem 0.55rem;
  }

  .figure {
    font-size: 2.35rem;
  }

  .countdown {
    font-size: 0.95rem;
  }

  .body-row {
    gap: 0.7rem;
    margin-top: 0.5rem;
  }

  .meters {
    gap: 0.5rem;
  }
}

/* Auf niedrigen Kiosk-Displays bleibt der Zustand kompakt und horizontal. */
@media (max-height: 600px) {
  .empty {
    grid-template-columns: 5.25rem minmax(0, 1fr);
    gap: 0.75rem;
    padding: 0.55rem 0.8rem;
  }

  .empty-stage {
    --mascot-size: 5.5rem;
  }
}

@media (max-width: 420px) {
  .brand-card {
    padding-inline: 0.8rem;
  }

  .empty {
    grid-template-columns: 4.5rem minmax(0, 1fr);
    gap: 0.65rem;
    padding-inline: 0.7rem;
  }

  .empty-stage {
    --mascot-size: 4.75rem;
  }
}
</style>
