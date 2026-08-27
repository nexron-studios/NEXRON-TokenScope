import { watch } from 'vue'
import { useSettings } from '@/composables/useSettings'
import type { WindowSize } from '@/composables/useSettings'

/**
 * Fenstermaße je Stufe in logischen Pixeln. `medium` entspricht der Größe, mit
 * der die Hülle das Fenster ohnehin baut (main.rs); `small` bleibt bewusst über
 * dem 1024 × 600 des Panels, damit die Kacheln nicht in die schmalen
 * Media-Query-Zweige fallen.
 */
const WINDOW_SIZES: Record<WindowSize, { width: number; height: number }> = {
  small: { width: 1024, height: 640 },
  medium: { width: 1280, height: 800 },
  large: { width: 1600, height: 1000 },
}

/**
 * Dieselbe Oberfläche läuft im Browser und in der Tauri-Hülle. Nur dort gibt es
 * ein Fenster, dessen Größe sie setzen darf – erkennbar an dem, was die Hülle
 * in die Seite injiziert.
 */
export const isDesktopShell = (): boolean =>
  typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window

export function useDesktopWindow() {
  const { settings } = useSettings()

  const applySize = async (size: WindowSize, isUserChoice: boolean) => {
    if (!isDesktopShell()) return

    // Erst laden, wenn wirklich in der Hülle: im Browser gäbe es nichts, womit
    // das Modul reden könnte.
    const { getCurrentWindow, LogicalSize } = await import('@tauri-apps/api/window')
    const appWindow = getCurrentWindow()

    // Auf dem Kiosk läuft das Fenster im Vollbild. Beim Start bleibt es das
    // auch – sonst nähme eine gespeicherte Stufe dem Panel den Vollbildmodus.
    // Wählt jemand die Größe dagegen selbst aus, ist das Verlassen gemeint.
    const isFullscreen = await appWindow.isFullscreen()
    if (isFullscreen && !isUserChoice) return
    if (isFullscreen) await appWindow.setFullscreen(false)

    const { width, height } = WINDOW_SIZES[size]
    await appWindow.setSize(new LogicalSize(width, height))
  }

  watch(
    () => settings.value.windowSize,
    (size, previous) => void applySize(size, previous !== undefined),
    { immediate: true },
  )
}
