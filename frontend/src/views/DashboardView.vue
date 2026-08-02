<script setup lang="ts">
import { computed } from 'vue'
import AlertBanner from '@/components/AlertBanner.vue'
import ProviderCard from '@/components/ProviderCard.vue'
import UsageHistoryChart from '@/components/UsageHistoryChart.vue'
import type { HistoryResponse, ProviderUsage } from '@/api/types'

const props = defineProps<{
  providers: ProviderUsage[]
  history?: HistoryResponse
  historyHours: number
  backendError?: string
  backendHint?: string
  loading?: boolean
  largeText: boolean
}>()

defineEmits<{ retry: [] }>()

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

    <div v-if="providers.length" class="cards">
      <ProviderCard
        v-for="provider in providers"
        :key="provider.id"
        :provider="provider"
        :large="largeText"
        :backend-down="Boolean(backendError)"
      />
    </div>

    <!-- Steht schon ein Banner oben, wäre dieser Hinweis nur ein zweiter
         Grund für dieselbe leere Fläche. -->
    <p v-else-if="!backendError" class="empty">
      Kein Anbieter aktiv. In den Einstellungen wieder einschalten.
    </p>

    <UsageHistoryChart
      :history="history"
      :hours="historyHours"
      :visible-providers="visibleIds"
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

.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(19rem, 1fr));
  gap: 0.75rem;
  flex: 1;
  min-height: 0;
}

.empty {
  display: grid;
  place-items: center;
  flex: 1;
  border: 1px solid rgb(255 255 255 / 8%);
  border-radius: 0.9rem;
  background: rgb(255 255 255 / 2%);
  color: #82828b;
  font-size: 0.8125rem;
  padding: 0.7rem 0.95rem;
}
</style>
