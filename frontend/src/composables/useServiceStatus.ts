import { computed, onBeforeUnmount, onMounted, shallowRef, watch } from 'vue'
import { useIntervalFn } from '@vueuse/core'
import { api } from '@/api/client'
import type { ServiceStatus } from '@/api/types'
import { useSettings } from '@/composables/useSettings'

/** Das Backend hält den Stand eine Minute, während einer Störung 20 s. */
const POLL_INTERVAL_MS = 30 * 1000

/**
 * Lage der Anbieter-Statusseiten, geholt über das eigene Backend.
 *
 * Wie beim Wetter bleiben Fehler hier: Ein klemmender Abruf ist kein Fehler
 * des Dashboards. Der vorige Stand bleibt stehen, und ob er noch etwas taugt,
 * sagt das Backend über `stale`.
 */
export const useServiceStatus = () => {
  const { settings } = useSettings()

  const allStatuses = shallowRef<ServiceStatus[]>([])
  let controller: AbortController | undefined

  // Ein ausgeblendeter Anbieter soll auch mit seiner Störung nicht auftauchen.
  const serviceStatuses = computed(() =>
    allStatuses.value.filter((status) => settings.value.enabledProviders[status.provider]),
  )

  const load = async () => {
    if (!settings.value.showServiceStatus) {
      allStatuses.value = []
      return
    }

    controller?.abort()
    controller = new AbortController()

    try {
      // `?? []`: Ein Backend, das noch nicht neu gestartet wurde, antwortet
      // hier im alten Format. Dann fehlt die Anzeige, statt die Kopfzeile
      // mitzureißen.
      allStatuses.value = (await api.serviceStatus(controller.signal)).providers ?? []
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      // Das Backend fehlt ganz – dafür zeigt das Dashboard schon ein Banner.
      console.warn('service_status.load_failed', { error })
    }
  }

  const { pause, resume } = useIntervalFn(load, POLL_INTERVAL_MS, { immediate: false })

  watch(
    () => settings.value.showServiceStatus,
    () => void load(),
  )

  onMounted(() => {
    void load()
    resume()
  })

  onBeforeUnmount(() => {
    pause()
    controller?.abort()
  })

  return { serviceStatuses }
}
