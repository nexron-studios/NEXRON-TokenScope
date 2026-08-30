import { computed, onBeforeUnmount, onMounted, watch } from 'vue'
import { useDocumentVisibility, useIntervalFn } from '@vueuse/core'
import type { Ref } from 'vue'

interface RefreshOptions {
  autoRefresh: Ref<boolean>
  intervalSeconds: Ref<number>
  refresh: () => Promise<void>
  /** Beim Oeffnen einmal wirklich neu pollen; Intervalle lesen den Backend-Cache. */
  initialRefresh?: () => Promise<void>
}

/**
 * Kuerzester Abstand zwischen zwei erzwungenen Polls. Ein erzwungener Abruf
 * umgeht die Bremse des Backends, also muss die Bremse hier sitzen.
 */
const FORCED_REFRESH_MIN_GAP_MS = 5_000

export function useUsageRefresh(options: RefreshOptions) {
  const visibility = useDocumentVisibility()
  const interval = computed(() =>
    Math.max(15, options.intervalSeconds.value) * 1_000,
  )

  let lastForcedAt = 0

  const forceRefresh = async () => {
    const moment = Date.now()
    if (moment - lastForcedAt < FORCED_REFRESH_MIN_GAP_MS) return
    lastForcedAt = moment
    await (options.initialRefresh ?? options.refresh)()
  }

  const { pause, resume, isActive } = useIntervalFn(
    () => void options.refresh(),
    interval,
    { immediate: false, immediateCallback: false },
  )

  const syncInterval = () => {
    if (options.autoRefresh.value && visibility.value === 'visible') {
      resume()
    } else {
      pause()
    }
  }

  watch([options.autoRefresh, visibility], syncInterval)

  // Beim Zurueckkommen holt `resume()` nur den Timer zurueck, nicht den Stand -
  // die Oberflaeche zeigte bis zum naechsten Intervall weiter den alten Wert,
  // und nur der Knopf half. Erzwungen statt aus dem Cache, weil nach einem
  // Ruhezustand auch die Schleife des Backends hinterherhaengt.
  watch(visibility, (current, previous) => {
    if (current !== 'visible' || previous === 'visible') return
    if (!options.autoRefresh.value) return
    void forceRefresh()
  })

  onMounted(() => {
    void forceRefresh()
    syncInterval()
  })

  onBeforeUnmount(pause)

  return {
    isAutoRefreshActive: isActive,
    documentVisibility: visibility,
  }
}
