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

export function useUsageRefresh(options: RefreshOptions) {
  const visibility = useDocumentVisibility()
  const interval = computed(() =>
    Math.max(15, options.intervalSeconds.value) * 1_000,
  )

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

  onMounted(() => {
    void (options.initialRefresh ?? options.refresh)()
    syncInterval()
  })

  onBeforeUnmount(pause)

  return {
    isAutoRefreshActive: isActive,
    documentVisibility: visibility,
  }
}
