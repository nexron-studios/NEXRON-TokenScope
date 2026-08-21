<script setup lang="ts">
import { computed } from 'vue'
import AlertBanner from '@/components/AlertBanner.vue'
import ProviderCard from '@/components/ProviderCard.vue'
import ProviderCardPlaceholder from '@/components/ProviderCardPlaceholder.vue'
import UsageHistoryChart from '@/components/UsageHistoryChart.vue'
import { useI18n } from '@/composables/useI18n'
import type { HistoryResponse, ProviderUsage } from '@/api/types'

const props = defineProps<{
  providers: ProviderUsage[]
  history?: HistoryResponse
  historyHours: number
  backendError?: string
  backendHint?: string
  loading?: boolean
  historyLoading?: boolean
  placeholderCount?: number
  largeText: boolean
}>()

defineEmits<{ retry: [] }>()

const { t } = useI18n()

const visibleIds = computed(() => props.providers.map((provider) => provider.id))
</script>

<template>
  <main class="view">
    <AlertBanner
      v-if="backendError"
      :title="backendError"
      :hint="backendHint"
      :busy="loading"
      @retry="$emit('retry')"
    />

    <div v-if="providers.length" class="cards" :aria-busy="loading">
      <ProviderCard
        v-for="provider in providers"
        :key="provider.id"
        :provider="provider"
        :large="largeText"
        :backend-down="Boolean(backendError)"
      />
    </div>

    <div
      v-else-if="loading && !backendError && placeholderCount"
      class="cards"
      aria-busy="true"
      :aria-label="t('dashboard.loading')"
    >
      <ProviderCardPlaceholder
        v-for="index in placeholderCount"
        :key="index"
      />
    </div>

    <!-- Steht schon ein Banner oben, wäre dieser Hinweis nur ein zweiter
         Grund für dieselbe leere Fläche. -->
    <p v-else-if="!backendError" class="empty">
      {{ t('dashboard.noProviders') }}
    </p>

    <UsageHistoryChart
      class="history"
      :history="history"
      :hours="historyHours"
      :visible-providers="visibleIds"
      :loading="historyLoading"
    />
  </main>
</template>

<style scoped>
/* Flex statt Grid: Das Banner kommt und geht, der Rumpf soll deshalb nicht
   in eine andere Zeilenspur rutschen. */
.view {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  flex: 1;
  min-height: 0;
}

/* `flex: 0 1 auto`: Die Kacheln nehmen sich die Höhe, die ihr Inhalt braucht,
   und geben sie nur her, wenn es sonst nicht reicht. Alles darüber hinaus
   gehört dem Verlauf – sonst stünde in jeder Kachel ein leeres Feld unter den
   Balken. */
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(19rem, 1fr));
  gap: 0.75rem;
  flex: 0 1 auto;
  min-height: 0;
}

.history {
  flex: 1 1 0;
  min-height: 8rem;
}

.empty {
  display: grid;
  place-items: center;
  flex: 1;
  border: 1px solid rgb(255 255 255 / 8%);
  border-radius: 0.9rem;
  background: rgb(255 255 255 / 2%);
  color: #bcbcc5;
  font-size: 0.8125rem;
  padding: 0.7rem 0.95rem;
}
</style>
