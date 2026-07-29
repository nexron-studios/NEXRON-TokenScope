import { computed, onBeforeUnmount, ref } from 'vue'
import { useOnline } from '@vueuse/core'
import { ChatGPTUsageProvider } from '@/services/chatgpt/ChatGPTUsageProvider'
import { ClaudeUsageProvider } from '@/services/claude/ClaudeUsageProvider'
import type {
  AIUsageService,
  ServiceId,
  UsageProvider,
} from '@/services/usage.types'
import type { AppSettings } from '@/composables/useSettings'
import type { Ref } from 'vue'

const SERVICE_ORDER: ServiceId[] = ['chatgpt', 'claude']

export function useAIUsage(settings: Ref<AppSettings>) {
  const services = ref<AIUsageService[]>([])
  const loading = ref(false)
  const refreshError = ref<string>()
  const lastRefreshAt = ref<string>()
  const isOnline = useOnline()
  let controller: AbortController | undefined

  const providers = (): Record<ServiceId, UsageProvider> => ({
    chatgpt: new ChatGPTUsageProvider(
      settings.value.mockEnabled,
      settings.value.manualValues.chatgpt,
    ),
    claude: new ClaudeUsageProvider(
      settings.value.mockEnabled,
      settings.value.manualValues.claude,
    ),
  })

  const refresh = async () => {
    controller?.abort()
    controller = new AbortController()
    const currentController = controller
    loading.value = true
    refreshError.value = undefined

    try {
      const activeProviders = providers()
      const results = await Promise.allSettled(
        SERVICE_ORDER.map((id) =>
          activeProviders[id].getUsage(currentController.signal),
        ),
      )

      if (currentController.signal.aborted) return

      services.value = results.map((result, index) => {
        if (result.status === 'fulfilled') return result.value

        const id = SERVICE_ORDER[index] ?? 'chatgpt'
        return {
          id,
          name: id === 'chatgpt' ? 'ChatGPT' : 'Claude',
          updatedAt: new Date().toISOString(),
          status: 'unavailable',
          dataSource: settings.value.mockEnabled ? 'mock' : 'manual',
          error: 'Nutzungsdaten konnten nicht geladen werden.',
        }
      })

      lastRefreshAt.value = new Date().toISOString()

      if (results.every((result) => result.status === 'rejected')) {
        refreshError.value = 'Nutzungsdaten konnten nicht geladen werden.'
      }
    } finally {
      if (!currentController.signal.aborted) {
        loading.value = false
      }
    }
  }

  const visibleServices = computed(() =>
    services.value.filter(
      (service) => settings.value.enabledServices[service.id],
    ),
  )

  onBeforeUnmount(() => controller?.abort())

  return {
    services,
    visibleServices,
    loading,
    refreshError,
    lastRefreshAt,
    isOnline,
    refresh,
  }
}
