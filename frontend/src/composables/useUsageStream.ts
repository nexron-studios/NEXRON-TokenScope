import { onBeforeUnmount, onMounted } from 'vue'
import type { UsageResponse } from '@/api/types'

/** Derselbe relative Pfad wie in `api/client.ts` – Dev-Proxy wie Kiosk-Build. */
const BASE = import.meta.env.VITE_API_BASE ?? ''

/**
 * Hört auf den Push-Kanal des Backends und meldet jeden neuen Stand.
 *
 * Das Intervall aus `useUsageRefresh` bleibt daneben bestehen: Der Strom kommt
 * ihm zuvor, ersetzt es aber nicht – steht die Verbindung, liefert aber nichts
 * mehr, holt das Intervall den Stand weiterhin ab.
 */
export function useUsageStream(onSnapshot: (snapshot: UsageResponse) => void) {
  let source: EventSource | undefined

  const close = () => {
    source?.close()
    source = undefined
  }

  onMounted(() => {
    // Ein Verbindungsfehler braucht hier keine Behandlung: `EventSource`
    // verbindet von selbst neu und schickt danach sofort den aktuellen Stand.
    source = new EventSource(`${BASE}/api/events`)
    source.onmessage = (event) => {
      try {
        onSnapshot(JSON.parse(event.data) as UsageResponse)
      } catch (error) {
        console.warn('usage.stream_unreadable', error)
      }
    }
  })

  onBeforeUnmount(close)
}
