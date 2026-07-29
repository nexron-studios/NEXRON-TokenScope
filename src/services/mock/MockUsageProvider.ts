import type {
  AIUsageService,
  ServiceId,
  UsageProvider,
} from '@/services/usage.types'

interface MockDefinition {
  id: ServiceId
  name: string
  plan: string
  remainingPercentage: number
  resetHours: number
}

const MOCKS: Record<ServiceId, MockDefinition> = {
  chatgpt: {
    id: 'chatgpt',
    name: 'ChatGPT',
    plan: 'Plus · Demo',
    remainingPercentage: 72,
    resetHours: 3.25,
  },
  claude: {
    id: 'claude',
    name: 'Claude',
    plan: 'Pro · Demo',
    remainingPercentage: 46,
    resetHours: 5.5,
  },
}

export class MockUsageProvider implements UsageProvider {
  constructor(private readonly id: ServiceId) {}

  async getUsage(): Promise<AIUsageService> {
    const definition = MOCKS[this.id]
    const now = Date.now()

    return {
      id: definition.id,
      name: definition.name,
      plan: definition.plan,
      usedPercentage: 100 - definition.remainingPercentage,
      remainingPercentage: definition.remainingPercentage,
      usageText: `${100 - definition.remainingPercentage} % verbraucht`,
      resetAt: new Date(now + definition.resetHours * 60 * 60 * 1_000).toISOString(),
      updatedAt: new Date(now).toISOString(),
      status: 'unavailable',
      dataSource: 'mock',
    }
  }
}
