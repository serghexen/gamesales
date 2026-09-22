<template>
  <section class="catalog-routing" aria-labelledby="catalog-routing-title">
    <div class="catalog-routing__heading">
      <h4 id="catalog-routing-title">Приоритет поставщиков</h4>
      <span class="muted">{{ offers.filter((offer) => offer.fulfillment_enabled).length }} из {{ offers.length }} включено</span>
    </div>
    <p class="muted catalog-routing__hint">Сверху вниз. Перетащите строку или используйте стрелки. Отключённые поставщики пропускаются.</p>
    <ol v-if="offers.length" class="catalog-routing__list" aria-label="Порядок поставщиков">
      <li v-for="(offer, index) in offers" :key="offer.offer_id" class="catalog-routing__row" :class="{ 'is-disabled': !offer.fulfillment_enabled, 'is-target': target === index && dragged !== null }"
        :data-test="`catalog-routing-${offer.offer_id}`" @dragover="dragOver($event, index)" @dragleave="target = null" @drop="drop($event, index)">
        <button class="catalog-routing__handle" type="button" :draggable="!disabled" :disabled="disabled" tabindex="-1" :aria-label="`Перетащить ${offer.supplier_name}`" title="Перетащить поставщика" @dragstart="dragStart($event, index)" @dragend="dragEnd">
          <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M7 4v.1M13 4v.1M7 10v.1M13 10v.1M7 16v.1M13 16v.1" /></svg>
        </button>
        <span class="catalog-routing__rank">{{ index + 1 }}</span>
        <div class="catalog-routing__supplier"><strong>{{ offer.supplier_name }}</strong><span class="muted">{{ offer.service_title }} · {{ offer.nominal_title }}</span></div>
        <div class="catalog-routing__snapshot"><strong>{{ price(offer) }}</strong><span class="muted">Остаток: {{ offer.stock_count ?? '—' }}<template v-if="offer.stock_count === 0"> · Нет в наличии</template></span></div>
        <div class="catalog-routing__controls">
          <button type="button" :disabled="disabled || index === 0" :aria-label="`Выше: ${offer.supplier_name}`" title="Выше" @click="$emit('move', index, index - 1)">↑</button>
          <button type="button" :disabled="disabled || index === offers.length - 1" :aria-label="`Ниже: ${offer.supplier_name}`" title="Ниже" @click="$emit('move', index, index + 1)">↓</button>
        </div>
        <label class="catalog-routing__toggle" :title="offer.fulfillment_enabled ? 'Использовать в автовыдаче' : 'Не использовать в автовыдаче'">
          <input type="checkbox" role="switch" :checked="offer.fulfillment_enabled" :disabled="disabled" :aria-label="`Автовыдача: ${offer.supplier_name}`" @change="$emit('toggle', offer.offer_id, $event.target.checked)">
          <span aria-hidden="true"></span>
        </label>
      </li>
    </ol>
    <p v-else class="catalog-routing__empty muted">Поставщики ещё не связаны с этим номиналом.</p>
    <p v-if="offers.length && !offers.some((offer) => offer.fulfillment_enabled)" class="catalog-routing__hint muted" role="status">Все поставщики отключены от автовыдачи. Связки, цены и остатки сохранены.</p>
  </section>
</template>

<script setup>
import { ref } from 'vue'
const props = defineProps({ offers: { type: Array, required: true }, disabled: Boolean })
const emit = defineEmits(['move', 'toggle'])
const dragged = ref(null)
const target = ref(null)

function price(offer) {
  // Показываем сохранённую закупочную цену, чтобы приоритет можно было сравнить без запроса поставщику.
  return offer.price == null ? '—' : new Intl.NumberFormat('ru-RU', { style: 'currency', currency: offer.currency }).format(Number(offer.price))
}

function dragStart(event, index) {
  // Перенос начинается за отдельную ручку и не мешает переключателям или выделению текста.
  if (props.disabled) { event.preventDefault(); return }
  dragged.value = index
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', String(props.offers[index].offer_id))
  }
}

function dragOver(event, index) {
  // Принимаем только внутренний перенос этой карточки, не внешние данные.
  if (props.disabled || dragged.value === null) return
  event.preventDefault()
  target.value = index
  if (event.dataTransfer) event.dataTransfer.dropEffect = 'move'
}

function drop(event, index) {
  // Перестановка остаётся в черновике до общего сохранения карточки.
  event.preventDefault()
  if (!props.disabled && dragged.value !== null) emit('move', dragged.value, index)
  dragEnd()
}

function dragEnd() {
  // Убираем подсветку и при успешном переносе, и при отмене за пределами списка.
  dragged.value = null
  target.value = null
}
</script>

<style scoped>
.catalog-routing { min-width: 0; }
.catalog-routing__heading { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.catalog-routing__heading h4 { margin: 0; font-size: 13px; font-weight: 650; }
.catalog-routing__heading > span { font-size: 11px; }
.catalog-routing__hint { margin: 6px 0 10px; font-size: 12px; line-height: 1.5; }
.catalog-routing__list { list-style: none; margin: 0; padding: 0; border: 1px solid var(--stroke); border-radius: 10px; max-height: 280px; overflow-y: auto; overscroll-behavior: contain; }
.catalog-routing__row { display: grid; grid-template-columns: 18px 20px minmax(0, 1fr) auto auto 32px; gap: 9px; align-items: center; padding: 10px; border-bottom: 1px solid var(--stroke); background: rgba(84,213,173,.025); }
.catalog-routing__row:last-child { border-bottom: 0; }
.catalog-routing__row.is-target { box-shadow: inset 0 2px #54d5ad; background: rgba(84,213,173,.09); }
.catalog-routing__rank { color: #54d5ad; font-size: 12px; text-align: center; font-variant-numeric: tabular-nums; }
.catalog-routing__supplier, .catalog-routing__snapshot { min-width: 0; display: grid; gap: 3px; font-size: 12px; }
.catalog-routing__supplier strong { font-weight: 600; }
.catalog-routing__supplier span { font-size: 11px; overflow-wrap: anywhere; }
.catalog-routing__snapshot { text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }
.catalog-routing__snapshot span { font-size: 11px; }
.catalog-routing__row.is-disabled .catalog-routing__supplier, .catalog-routing__row.is-disabled .catalog-routing__rank { opacity: .5; }
.catalog-routing__controls { display: flex; gap: 3px; }
.catalog-routing__controls button, .catalog-routing__handle { padding: 0; width: 26px; height: 28px; border: 1px solid var(--stroke); border-radius: 6px; background: transparent; color: var(--muted); cursor: pointer; font-size: 16px; }
.catalog-routing .catalog-routing__handle { width: 18px; border: 0; cursor: grab; }
.catalog-routing__handle svg { width: 16px; height: 20px; fill: none; stroke: currentColor; stroke-width: 3; stroke-linecap: round; }
.catalog-routing button:disabled { opacity: .3; cursor: default; }
.catalog-routing button:focus-visible { outline: 2px solid #54d5ad; outline-offset: 2px; }
.catalog-routing__toggle { position: relative; width: 32px; height: 20px; cursor: pointer; }
.catalog-routing__toggle input { position: absolute; inset: 0; margin: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer; }
.catalog-routing__toggle span { display: block; height: 20px; border-radius: 12px; background: var(--stroke); pointer-events: none; }
.catalog-routing__toggle span::after { content: ''; position: absolute; top: 3px; left: 3px; width: 14px; height: 14px; border-radius: 50%; background: var(--muted); transition: transform .15s; }
.catalog-routing__toggle input:checked + span { background: rgba(84,213,173,.25); }
.catalog-routing__toggle input:checked + span::after { transform: translateX(12px); background: #54d5ad; }
.catalog-routing__toggle input:focus-visible + span { outline: 2px solid #54d5ad; outline-offset: 3px; }
.catalog-routing__toggle input:disabled + span { opacity: .5; }
.catalog-routing__empty { margin: 0; padding: 14px; border: 1px dashed var(--stroke); border-radius: 9px; font-size: 12px; }
@media (max-width: 580px) {
  .catalog-routing__row { grid-template-columns: 18px 18px minmax(0, 1fr) auto 32px; gap: 6px; }
  .catalog-routing__snapshot { grid-column: 3; grid-row: 2; display: flex; flex-wrap: wrap; gap: 6px; text-align: left; }
  .catalog-routing__controls { grid-column: 4; grid-row: 1 / 3; }
  .catalog-routing__toggle { grid-column: 5; grid-row: 1 / 3; }
}
</style>
