<script setup lang="ts">
import { computed } from "vue";
import { useNow } from "@vueuse/core";
import { useI18n } from "@/composables/useI18n";
import { useWeather } from "@/composables/useWeather";
import WeatherBadge from "@/components/WeatherBadge.vue";
import ServiceStatusBadge from "@/components/ServiceStatusBadge.vue";
import type { ServiceStatus } from "@/api/types";
import nexronLogo from "@/assets/logos/nexron_logo.svg";
import {
  ChartColumn,
  Gauge,
  RefreshCw,
  Settings,
  type LucideIcon,
} from "@lucide/vue";

export type ViewId = "dashboard" | "logs" | "settings";

defineProps<{
  view: ViewId;
  loading: boolean;
  connected: boolean;
  demo: boolean;
  serviceStatuses: ServiceStatus[];
}>();

defineEmits<{ navigate: [ViewId]; refresh: [] }>();

const now = useNow();
const { locale, t } = useI18n();
const { weather } = useWeather();
const clock = computed(() =>
  new Intl.DateTimeFormat(locale.value, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(now.value),
);

const tabs = computed<Array<{ id: ViewId; label: string; icon: LucideIcon }>>(
  () => [
    { id: "dashboard", label: t("nav.dashboard"), icon: Gauge },
    { id: "logs", label: t("nav.logs"), icon: ChartColumn },
    { id: "settings", label: t("nav.settings"), icon: Settings },
  ],
);
</script>

<template>
  <header class="head">
    <!-- Reicht die Breite nicht, wird hier abgeschnitten statt über die
         Reiter gemalt. Die Reihenfolge ist die Wichtigkeit von vorn: Was
         hinten steht, gibt zuerst nach. -->
    <div class="flex min-w-0 items-center gap-[0.7rem] overflow-hidden">
      <!-- Reine Herkunftsangabe: Der Schriftzug trägt keine Information, die
           nicht anderswo steht, deshalb bleibt er aus dem Vorlesefluss – und
           räumt als Erstes den Platz, wenn der Bildschirm schmal wird.
           Verkleinern ist keine Option: Unter etwa 1.4rem Höhe zerfällt seine
           untere Zeile auf dem Panel zu einem grauen Balken. -->
      <img
        :src="nexronLogo"
        class="hidden h-[1.45rem] w-auto flex-none lg:block"
        alt=""
        aria-hidden="true"
      />
      <span class="divider max-lg:hidden" />
      <span class="clock shrink-0">{{ clock }}</span>
      <span class="divider" />
      <span
        class="flex shrink-0 items-center gap-[0.4rem] text-xs font-bold whitespace-nowrap"
        :class="connected ? 'text-[#4f9d6d]' : 'text-[#d03b3b]'"
        :title="connected ? t('nav.local') : t('nav.offline')"
      >
        <span class="size-[0.45rem] rounded-full bg-current" aria-hidden="true" />
        <!-- Schmal bleibt nur der Punkt; der Text geht an den Screenreader
             und steht im Tooltip. Offline zeigt ohnehin ein Banner. -->
        <span class="max-lg:sr-only">{{ connected ? t("nav.local") : t("nav.offline") }}</span>
      </span>
      <span v-if="demo" class="demo">Demo</span>

      <template v-if="serviceStatuses.length">
        <span class="divider" />
        <ServiceStatusBadge
          v-for="status in serviceStatuses"
          :key="status.provider"
          :status="status"
        />
      </template>

      <!-- Das Wetter ist das Entbehrlichste in der Zeile: Schmal verschwindet
           es ganz, statt den Anbieterstatus anzuschneiden. -->
      <template v-if="weather">
        <span class="divider max-md:hidden" />
        <WeatherBadge class="max-md:hidden" :report="weather" />
      </template>
    </div>

    <nav class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        class="tab"
        :class="{ active: view === tab.id }"
        :aria-current="view === tab.id ? 'page' : undefined"
        :title="tab.label"
        @click="$emit('navigate', tab.id)"
      >
        <component :is="tab.icon" class="size-4 shrink-0" aria-hidden="true" />
        <!-- Unter 1280 px nur das Symbol: Die drei Beschriftungen kosten
             ~250 px, und auf dem 1024er-Panel verdrängten sie den Status. -->
        <span class="max-xl:sr-only">{{ tab.label }}</span>
      </button>

      <button
        type="button"
        class="tab icon"
        :disabled="loading"
        :aria-label="t('nav.refresh')"
        @click="$emit('refresh')"
      >
        <RefreshCw
          class="size-5"
          :class="{ 'animate-spin': loading }"
          aria-hidden="true"
        />
      </button>
    </nav>
  </header>
</template>

<style scoped>
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  height: 3.625rem;
  flex-shrink: 0;
}



.clock {
  font-size: 1.35rem;
  font-variant-numeric: tabular-nums;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.divider {
  width: 1px;
  height: 1.1rem;
  background: rgb(255 255 255 / 12%);
}





.demo {
  border: 1px solid rgb(250 178 25 / 45%);
  border-radius: 999px;
  color: #fab219;
  font-size: 0.625rem;
  font-weight: 800;
  letter-spacing: 0.09em;
  padding: 0.15rem 0.5rem;
  text-transform: uppercase;
}

.tabs {
  display: flex;
  gap: 0.3rem;
  border: 1px solid rgb(255 255 255 / 8%);
  border-radius: 0.9rem;
  background: rgb(255 255 255 / 3%);
  padding: 0.25rem;
}

.tab {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  min-height: 3rem;
  border: 0;
  border-radius: 0.65rem;
  background: transparent;
  color: #ccccd3;
  font-size: 0.8125rem;
  font-weight: 700;
  padding: 0 0.95rem;
  touch-action: manipulation;
  transition:
    background 140ms ease,
    color 140ms ease;
}

.tab:active {
  background: rgb(255 255 255 / 6%);
}

.tab.active {
  background: rgb(255 255 255 / 12%);
  color: #fff;
}

.tab.icon {
  display: grid;
  place-items: center;
  min-width: 2.75rem;
  padding: 0;
}

.tab:disabled {
  opacity: 0.5;
}

</style>
