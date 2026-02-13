<template>
  <div v-if="productsTotal > 0" class="pager">
    <span class="muted">Всего: {{ productsTotal }}</span>
    <label class="pager__size">
      <span class="label">Показывать</span>
      <select :value="productsPageSize" class="input input--select input--compact" @change="setProductsPageSize($event)">
        <option :value="20">20</option>
        <option :value="50">50</option>
        <option :value="100">100</option>
      </select>
    </label>
    <button class="ghost" @click="setProductsPage(1)" :disabled="productsPage <= 1">
      «
    </button>
    <button class="ghost" @click="prevProductsPage" :disabled="productsPage <= 1">
      ← Назад
    </button>
    <label class="pager__jump">
      <span class="muted">Стр.</span>
      <input
        :value="productsPageInput"
        class="input input--compact input--page"
        type="number"
        min="1"
        :max="productsTotalPages"
        @input="setProductsPageInput($event)"
        @keydown.enter.prevent="jumpProductsPage"
        @blur="jumpProductsPage"
      />
    </label>
    <span class="muted">из {{ productsTotalPages }}</span>
    <button class="ghost" @click="nextProductsPage" :disabled="productsPage >= productsTotalPages">
      Вперёд →
    </button>
    <button class="ghost" @click="setProductsPage(productsTotalPages)" :disabled="productsPage >= productsTotalPages">
      »
    </button>
  </div>
</template>

<script setup>
defineProps({
  productsTotal: { type: Number, required: true },
  productsPageSize: { type: Number, required: true },
  setProductsPageSize: { type: Function, required: true },
  productsPage: { type: Number, required: true },
  setProductsPage: { type: Function, required: true },
  prevProductsPage: { type: Function, required: true },
  productsPageInput: { type: Number, required: true },
  setProductsPageInput: { type: Function, required: true },
  productsTotalPages: { type: Number, required: true },
  jumpProductsPage: { type: Function, required: true },
  nextProductsPage: { type: Function, required: true },
})
</script>
