import { onBeforeUnmount, ref, shallowRef } from 'vue'
import { api, errorText } from '@/api/client'
import type { HistoryResponse, LogGroupBy, LogSummary } from '@/api/types'
import { useI18n } from '@/composables/useI18n'

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

export function useLogSummary() {
  const { t } = useI18n()
  const summary = shallowRef<LogSummary>()
  const loading = ref(false)
  const error = ref<string>()
  let controller: AbortController | undefined

  const load = async (days: number, groupBy: LogGroupBy) => {
    controller?.abort()
    controller = new AbortController()
    const current = controller
    loading.value = true

    try {
      const next = await api.logs(days, groupBy, current.signal)
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

  onBeforeUnmount(() => controller?.abort())
  return { summary, loading, error, load }
}
