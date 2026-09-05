<template>
  <input
    class="input"
    type="number"
    min="0"
    step="0.01"
    :max="max"
    :value="voucherDeal && !deal.deal_id ? '' : deal.purchase_cost"
    :disabled="voucherDeal"
    :readonly="readonly"
    :title="voucherDeal ? 'Сохранённый закуп доступен только для просмотра. Новые покупки учитываются по ваучерам' : undefined"
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

// В сохранённых сделках показываем закуп, включая исторический; ручной ввод остаётся закрытым.
const voucherDeal = computed(() => isSupplierVoucherDeal(props.deal))

function updateManualCost(event) {
  // Заблокированное поле не меняет учёт даже при программно отправленном событии ввода.
  if (voucherDeal.value || props.readonly) return
  props.deal.purchase_cost = props.clampPrice(event.target.value === '' ? '' : Number(event.target.value))
}
</script>
