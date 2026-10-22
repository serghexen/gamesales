<template>
  <!-- Владелец видит закуп ваучеров, остальные роли — только закуп обычных услуг. -->
  <label v-if="canEnterCost" class="field">
    <span class="label">Закупочная цена</span>
    <input
      class="input"
      type="number"
      min="0"
      step="0.01"
      :max="max"
      :value="deal.purchase_cost"
      :readonly="readonly"
      @input="updateManualCost"
    />
  </label>
</template>

<script setup>
import { computed } from 'vue'
import { canEnterManualPurchaseCost } from '../dealsUtils.js'

const props = defineProps({
  deal: { type: Object, required: true },
  userRole: { type: String, default: '' },
  readonly: { type: Boolean, default: false },
  max: { type: Number, required: true },
  clampPrice: { type: Function, required: true },
})

// Проверяем роль и регион одинаково при создании, просмотре и редактировании.
const canEnterCost = computed(() => canEnterManualPurchaseCost(props.deal, props.userRole))

function updateManualCost(event) {
  // Разрешённый для роли закуп меняем только вне режима просмотра.
  if (!canEnterCost.value || props.readonly) return
  props.deal.purchase_cost = props.clampPrice(event.target.value === '' ? '' : Number(event.target.value))
}
</script>
