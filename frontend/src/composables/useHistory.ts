import { computed, onBeforeUnmount, ref, shallowRef, watch } from 'vue'
import { api, errorText } from '@/api/client'
import type { HistoryResponse, LogGroupBy, LogSummary } from '@/api/types'
import { useI18n } from '@/composables/useI18n'
import { useSettings } from '@/composables/useSettings'
import { excludedScopes } from '@/utils/scope'

export function useHistory() {
  const { t } = useI18n()
  const history = shallowRef<HistoryResponse>()
  const loading = ref(false)
  const error = ref<string>()
  let controller: AbortController | undefined

  const load = async (hours: number) => {
    controller?.abort()
    controller = new AbortController()
    const current = controller
    loading.value = true

    try {
      const next = await api.history(hours, current.signal)
      if (!current.signal.aborted) {
        history.value = next
        error.value = undefined
      }
    } catch (caught) {
      if (caught instanceof DOMException && caught.name === 'AbortError') return
      error.value = errorText(caught, t('error.history'))
    } finally {
      if (!current.signal.aborted) loading.value = false
    }
  }

  onBeforeUnmount(() => controller?.abort())
  return { history, loading, error, load }
}

/**
 * Die Auswertung folgt denselben Sichtbarkeits-Einstellungen wie das
 * Dashboard: Ein ausgeblendeter Login fehlt auch in Summen und Kennzahlen,
 * nicht nur in einer Liste.
 */
export function useLogSummary() {
  const { t } = useI18n()
  const { settings } = useSettings()
  const summary = shallowRef<LogSummary>()
  const loading = ref(false)
  const error = ref<string>()
  let controller: AbortController | undefined
  let lastRequest: { days: number; groupBy: LogGroupBy } | undefined

  const exclude = computed(() =>
    excludedScopes(settings.value.enabledProviders, settings.value.hiddenAccounts),
  )

  const load = async (days: number, groupBy: LogGroupBy) => {
    controller?.abort()
    controller = new AbortController()
    const current = controller
    lastRequest = { days, groupBy }
    loading.value = true

    try {
      const next = await api.logs(days, groupBy, exclude.value, current.signal)
      if (!current.signal.aborted) {
        summary.value = next
        error.value = undefined
      }
    } catch (caught) {
      if (caught instanceof DOMException && caught.name === 'AbortError') return
      error.value = errorText(caught, t('error.logs'))
    } finally {
      if (!current.signal.aborted) loading.value = false
    }
  }

  watch(exclude, () => {
    if (lastRequest) void load(lastRequest.days, lastRequest.groupBy)
  })

  onBeforeUnmount(() => controller?.abort())
  return { summary, loading, error, load }
}
