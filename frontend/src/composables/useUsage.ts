import { computed, onBeforeUnmount, ref, shallowRef } from 'vue'
import { api, ApiError } from '@/api/client'
import type { HealthResponse, UsageResponse } from '@/api/types'
import { useSettings } from '@/composables/useSettings'
import { useI18n } from '@/composables/useI18n'

/**
 * Holt den Zustand ausschließlich vom lokalen Backend. Das Frontend spricht
 * nie direkt mit einem Anbieter und sieht niemals ein Token.
 */
export function useUsage() {
  const { settings } = useSettings()
  const { t } = useI18n()

  const usage = shallowRef<UsageResponse>()
  const health = shallowRef<HealthResponse>()
  const loading = ref(false)
  const backendError = ref<string>()
  const backendHint = ref<string>()
  let controller: AbortController | undefined

  const providers = computed(() =>
    (usage.value?.providers ?? []).filter(
      (provider) => settings.value.enabledProviders[provider.id] !== false,
    ),
  )

  const isDemo = computed(() => usage.value?.demo_mode === true)

  const load = async (options: { refresh?: boolean } = {}) => {
    controller?.abort()
    controller = new AbortController()
    const current = controller
    loading.value = true

    try {
      const [nextUsage, nextHealth] = await Promise.all([
        api.usage({ refresh: options.refresh, signal: current.signal }),
        api.health(current.signal).catch(() => undefined),
      ])
      if (current.signal.aborted) return
      usage.value = nextUsage
      if (nextHealth) health.value = nextHealth
      backendError.value = undefined
      backendHint.value = undefined
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      const known = error instanceof ApiError
      backendError.value = known ? error.message : t('error.unexpectedLoad')
      backendHint.value = known
        ? error.hint
        : t('error.unexpectedHint')
    } finally {
      if (!current.signal.aborted) loading.value = false
    }
  }

  onBeforeUnmount(() => controller?.abort())

  return {
    usage,
    health,
    providers,
    isDemo,
    loading,
    backendError,
    backendHint,
    load,
  }
}
