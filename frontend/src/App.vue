<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useEventListener } from '@vueuse/core'
import AppHeader from '@/components/AppHeader.vue'
import type { ViewId } from '@/components/AppHeader.vue'
import { useHistory } from '@/composables/useHistory'
import { useI18n } from '@/composables/useI18n'
import { useSettings } from '@/composables/useSettings'
import { useUsage } from '@/composables/useUsage'
import { useUsageRefresh } from '@/composables/useUsageRefresh'
import DashboardView from '@/views/DashboardView.vue'
import LogsView from '@/views/LogsView.vue'
import SettingsView from '@/views/SettingsView.vue'

const { settings } = useSettings()
const { t } = useI18n()
const { usage, health, providers, isDemo, loading, backendError, backendHint, load } =
  useUsage()
const { history, load: loadHistory } = useHistory()

/**
 * Die Ansicht hängt am URL-Hash, damit der Kiosk-Browser direkt auf einer
 * bestimmten Seite starten kann (`#verbrauch`, `#einstellungen`).
 */
const VIEW_HASHES: Record<ViewId, string> = {
  dashboard: '',
  logs: '#verbrauch',
  settings: '#einstellungen',
}

const viewFromHash = (): ViewId => {
  const hash = window.location.hash
  const found = (Object.keys(VIEW_HASHES) as ViewId[]).find(
    (id) => VIEW_HASHES[id] === hash,
  )
  return found ?? 'dashboard'
}

const view = ref<ViewId>(viewFromHash())

const navigate = (next: ViewId) => {
  view.value = next
  const { pathname, search } = window.location
  window.history.replaceState(null, '', `${pathname}${search}${VIEW_HASHES[next]}`)
}

useEventListener(window, 'hashchange', () => {
  view.value = viewFromHash()
})

const refresh = async () => {
  await load()
  await loadHistory(settings.value.historyHours)
}

/** Der Aktualisieren-Knopf zwingt das Backend zu einem sofortigen Poll. */
const refreshNow = async () => {
  await load({ refresh: true })
  await loadHistory(settings.value.historyHours)
}

const { isAutoRefreshActive } = useUsageRefresh({
  autoRefresh: computed(() => settings.value.autoRefresh),
  intervalSeconds: computed(() => settings.value.refreshIntervalSeconds),
  refresh,
  // Ein Reload der Oberflaeche soll denselben Effekt wie der sichtbare
  // Aktualisieren-Knopf haben, ohne die periodischen API-Polls zu verdoppeln.
  initialRefresh: refreshNow,
})

watch(
  () => settings.value.historyHours,
  (hours) => void loadHistory(hours),
)

watch(
  () => settings.value.language,
  (language) => {
    document.documentElement.lang = language
  },
  { immediate: true },
)

const connected = computed(() => !backendError.value && Boolean(usage.value))

const shellClass = computed(() => ({
  kiosk: settings.value.kioskMode,
  night: settings.value.nightMode,
  large: settings.value.largeText,
}))
</script>

<template>
  <div class="shell" :class="shellClass">
    <AppHeader
      :view="view"
      :loading="loading"
      :connected="connected"
      :demo="isDemo"
      @navigate="navigate"
      @refresh="refreshNow"
    />

    <DashboardView
      v-if="view === 'dashboard'"
      :providers="providers"
      :history="history"
      :history-hours="settings.historyHours"
      :backend-error="backendError"
      :backend-hint="backendHint"
      :loading="loading"
      :large-text="settings.largeText"
      @retry="refreshNow"
    />
    <LogsView v-else-if="view === 'logs'" />
    <SettingsView v-else :health="health" @changed="refresh" />

    <footer class="foot">
      <span>
        <span class="pulse" :class="{ on: isAutoRefreshActive }" />
        {{ isAutoRefreshActive ? t('footer.auto') : t('footer.paused') }}
      </span>
      <span>
        {{ t('footer.sources', { seconds: usage?.poll_interval_seconds ?? 60 }) }}
      </span>
    </footer>
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  height: 100dvh;
  overflow: hidden;
  padding: 0.7rem 0.9rem 0.5rem;
}

/* Kiosk: kein Zeiger, keine Textauswahl beim Wischen. */
.shell.kiosk {
  cursor: none;
  user-select: none;
}

.shell.night {
  filter: brightness(0.62) saturate(0.9);
}

.shell.large {
  font-size: 1.06rem;
}

.foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-shrink: 0;
  color: #a4a4ae;
  font-size: 0.6875rem;
  padding: 0 0.15rem;
}

.foot > span {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.pulse {
  width: 0.4rem;
  height: 0.4rem;
  border-radius: 999px;
  background: #3d3d45;
}

.pulse.on {
  background: #4f9d6d;
}
</style>
