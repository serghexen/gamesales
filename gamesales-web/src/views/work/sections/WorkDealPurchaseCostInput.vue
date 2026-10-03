<template>
  <!-- В ваучерных сделках скрываем вместе поле и подпись, сохраняя закуп в учёте. -->
  <label v-if="!voucherDeal" class="field">
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
import { isSupplierVoucherDeal } from '../dealsUtils.js'

const props = defineProps({
  deal: { type: Object, required: true },
  readonly: { type: Boolean, default: false },
  max: { type: Number, required: true },
  clampPrice: { type: Function, required: true },
})

// Единое правило скрывает закуп ваучеров в новой и сохранённой карточке для всех ролей.
const voucherDeal = computed(() => isSupplierVoucherDeal(props.deal))

function updateManualCost(event) {
  // Ручной ввод меняет закуп только в обычной услуге и вне режима просмотра.
  if (voucherDeal.value || props.readonly) return
  props.deal.purchase_cost = props.clampPrice(event.target.value === '' ? '' : Number(event.target.value))
}
</script>
