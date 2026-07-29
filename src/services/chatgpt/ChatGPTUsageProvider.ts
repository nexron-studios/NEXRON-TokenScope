import { ManualUsageProvider } from '@/services/manual/ManualUsageProvider'
import { MockUsageProvider } from '@/services/mock/MockUsageProvider'
import { getPublicServiceStatus } from '@/services/status/statusPageClient'
import type {
  AIUsageService,
  ManualUsageValue,
  UsageProvider,
} from '@/services/usage.types'

const STATUS_ENDPOINT = 'https://status.openai.com/api/v2/status.json'

export class ChatGPTUsageProvider implements UsageProvider {
  constructor(
    private readonly useMock: boolean,
    private readonly manualValue: ManualUsageValue,
  ) {}

  async getUsage(signal?: AbortSignal): Promise<AIUsageService> {
    const usageProvider = this.useMock
      ? new MockUsageProvider('chatgpt')
      : new ManualUsageProvider({
          id: 'chatgpt',
          name: 'ChatGPT',
          value: this.manualValue,
        })

    const [usage, serviceStatus] = await Promise.all([
      usageProvider.getUsage(),
      getPublicServiceStatus(STATUS_ENDPOINT, signal),
    ])

    return {
      ...usage,
      status: serviceStatus.status,
      error:
        usage.error ??
        (serviceStatus.status === 'unavailable'
          ? 'Der öffentliche Dienststatus konnte nicht geladen werden.'
          : undefined),
    }
  }
}
