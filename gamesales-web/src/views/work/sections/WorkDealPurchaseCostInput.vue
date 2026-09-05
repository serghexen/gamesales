<template>
  <input
    class="input"
    type="number"
    min="0"
    step="0.01"
    :max="max"
    :value="voucherDeal ? '' : deal.purchase_cost"
    :disabled="voucherDeal"
    :readonly="readonly"
    :title="voucherDeal ? 'Закуп учитывается автоматически по купленным ваучерам' : undefined"
    @input="updateManualCost"
  />
</template>

<script setup>
import { computed } from 'vue'
import { isSupplierVoucherDeal } from '../dealsUtils.js'

const props = defineProps({
  deal: { type: Object, required: true },
  readonly: { type: Boolean, default: false },
  max: { type: Number, required: true },
  clampPrice: { type: Function, required: true },
})

// Показываем пустое ручное поле, не затирая загруженную сумму ваучеров в данных сделки.
const voucherDeal = computed(() => isSupplierVoucherDeal(props.deal))

function updateManualCost(event) {
  // Заблокированное поле не меняет учёт даже при программно отправленном событии ввода.
  if (voucherDeal.value || props.readonly) return
  props.deal.purchase_cost = props.clampPrice(event.target.value === '' ? '' : Number(event.target.value))
}
</script>
