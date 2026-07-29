import type {
  AIUsageService,
  ManualUsageValue,
  ServiceId,
  UsageProvider,
} from '@/services/usage.types'

interface ManualProviderOptions {
  id: ServiceId
  name: string
  value: ManualUsageValue
}

const clamp = (value: number) => Math.min(100, Math.max(0, value))

export class ManualUsageProvider implements UsageProvider {
  constructor(private readonly options: ManualProviderOptions) {}

  async getUsage(): Promise<AIUsageService> {
    const remaining = this.options.value.remainingPercentage
    const hasUsage = typeof remaining === 'number' && Number.isFinite(remaining)

    if (!hasUsage) {
      return {
        id: this.options.id,
        name: this.options.name,
        plan: this.options.value.plan || undefined,
        updatedAt: new Date().toISOString(),
        status: 'unavailable',
        dataSource: 'manual',
        error:
          'Keine Nutzungsdaten hinterlegt. In den Einstellungen kannst du einen manuellen Wert eintragen.',
      }
    }

    const safeRemaining = clamp(remaining)

    return {
      id: this.options.id,
      name: this.options.name,
      plan: this.options.value.plan || undefined,
      usedPercentage: 100 - safeRemaining,
      remainingPercentage: safeRemaining,
      usageText:
        this.options.value.usageText ||
        `${safeRemaining} % des Kontingents verfügbar`,
      resetAt: this.options.value.resetAt || undefined,
      updatedAt: new Date().toISOString(),
      status: 'unavailable',
      dataSource: 'manual',
    }
  }
}
