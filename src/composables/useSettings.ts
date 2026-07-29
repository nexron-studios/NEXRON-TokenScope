import { useLocalStorage } from '@vueuse/core'
import type {
  ManualUsageValue,
  ServiceId,
} from '@/services/usage.types'

export interface AppSettings {
  refreshIntervalSeconds: number
  autoRefresh: boolean
  mockEnabled: boolean
  compactView: boolean
  enabledServices: Record<ServiceId, boolean>
  manualValues: Record<ServiceId, ManualUsageValue>
}

export interface UsageImportFile {
  services: Array<{
    id: ServiceId
    plan?: string
    remainingPercentage?: number
    resetAt?: string
    usageText?: string
  }>
}

const createDefaultSettings = (): AppSettings => ({
  refreshIntervalSeconds: 60,
  autoRefresh: true,
  mockEnabled: true,
  compactView: false,
  enabledServices: {
    chatgpt: true,
    claude: true,
  },
  manualValues: {
    chatgpt: {
      plan: '',
      remainingPercentage: undefined,
      resetAt: '',
      usageText: '',
    },
    claude: {
      plan: '',
      remainingPercentage: undefined,
      resetAt: '',
      usageText: '',
    },
  },
})

const settings = useLocalStorage<AppSettings>(
  'ai-usage-monitor:settings',
  createDefaultSettings(),
  { mergeDefaults: true },
)

export function useSettings() {
  const resetSettings = () => {
    settings.value = createDefaultSettings()
  }

  const importUsage = (payload: UsageImportFile) => {
    if (!Array.isArray(payload.services)) {
      throw new Error('Die JSON-Datei enthält kein gültiges services-Array.')
    }

    let imported = 0

    for (const service of payload.services) {
      if (service.id !== 'chatgpt' && service.id !== 'claude') {
        continue
      }

      const remaining = service.remainingPercentage
      if (
        remaining !== undefined &&
        (!Number.isFinite(remaining) || remaining < 0 || remaining > 100)
      ) {
        throw new Error(
          `Der Wert für ${service.id} muss zwischen 0 und 100 liegen.`,
        )
      }

      settings.value.manualValues[service.id] = {
        plan: service.plan ?? '',
        remainingPercentage: remaining,
        resetAt: service.resetAt ?? '',
        usageText: service.usageText ?? '',
      }
      imported += 1
    }

    if (imported === 0) {
      throw new Error('Keine unterstützten Dienste in der JSON-Datei gefunden.')
    }

    settings.value.mockEnabled = false
    return imported
  }

  return {
    settings,
    resetSettings,
    importUsage,
  }
}
