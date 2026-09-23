import { onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { useIntervalFn } from '@vueuse/core'
import { api } from '@/api/client'
import type { WeatherReport } from '@/api/types'
import { useSettings } from '@/composables/useSettings'

/** Das Backend hält den Wert 15 Minuten; öfter zu fragen bringt denselben. */
const POLL_INTERVAL_MS = 15 * 60 * 1000

/**
 * Holt das Wetter vom eigenen Backend – nie direkt von einem Wetterdienst.
 * Das Frontend spricht mit genau einer Gegenstelle, so wie bei den
 * Kontingenten auch.
 *
 * Fehler bleiben hier: Es gibt kein `error`, das jemand anzeigen müsste. Der
 * Bericht ist dann `undefined` und die Kopfzeile zeigt ihn nicht. Ein
 * klemmender Wetterdienst darf im Dashboard kein Banner auslösen.
 */
export function useWeather() {
  const { settings } = useSettings()

  const weather = shallowRef<WeatherReport>()
  const loaded = ref(false)
  let controller: AbortController | undefined

  const load = async () => {
    if (!settings.value.showWeather) {
      weather.value = undefined
      return
    }

    controller?.abort()
    controller = new AbortController()

    try {
      weather.value = (await api.weather(controller.signal)) ?? undefined
    } catch {
      // Der vorige Bericht bleibt stehen. Ein zehn Minuten alter Wert ist
      // brauchbarer als eine Lücke, die beim nächsten Versuch wieder zugeht.
    } finally {
      loaded.value = true
    }
  }

  const { pause, resume } = useIntervalFn(load, POLL_INTERVAL_MS, {
    immediate: false,
  })

  // Der Schalter in den Einstellungen wirkt sofort – sonst bliebe die Anzeige
  // bis zum nächsten Intervall stehen, also im schlimmsten Fall eine
  // Viertelstunde nach dem Ausschalten.
  watch(
    () => settings.value.showWeather,
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

  return { weather, loaded, load }
}
