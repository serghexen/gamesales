<template>
  <section class="catalog-nominal" :class="{ 'is-open': expanded }" :data-nominal-id="nominal.catalog_nominal_id">
    <div class="catalog-nominal__summary">
      <div class="catalog-nominal__identity">
        <button class="catalog-nominal__expand" type="button" :disabled="!offers.length" :aria-expanded="expanded" :aria-controls="detailsId" :aria-label="`Поставщики номинала ${nominal.name}`" @click="expanded = !expanded">
          <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m7 4 6 6-6 6" /></svg>
        </button>
        <div class="catalog-nominal__name">
          <button v-if="canEdit" type="button" class="voucher-catalog__nominal" :disabled="saving" title="Открыть карточку номинала" @click="$emit('edit')">{{ nominal.name }}</button>
          <strong v-else>{{ nominal.name }}</strong>
          <span v-if="nominal.sku" class="catalog-nominal__sku" :aria-label="`SKU ${nominal.sku}`">{{ nominal.sku }}</span>
          <span class="catalog-nominal__count muted">{{ supplierCount }}</span>
        </div>
      </div>
      <div class="catalog-nominal__first">
        <template v-if="firstOffer"><strong>{{ firstOffer.supplier_name }}</strong><span class="muted">Первый по приоритету</span></template>
        <template v-else-if="offers.length"><span class="muted">Автовыдача отключена</span><span class="muted">Все поставщики выключены</span></template>
        <template v-else><span class="muted">Нет связки</span><button v-if="canEdit" class="catalog-nominal__action" type="button" :disabled="saving" @click="$emit('edit')">Связать</button></template>
      </div>
      <WorkVoucherCatalogSnapshot class="catalog-nominal__price" :offer="firstOffer" kind="price" compact :now="now" />
      <WorkVoucherCatalogSnapshot class="catalog-nominal__stock" :offer="firstOffer" kind="stock" compact :now="now" />
      <button v-if="canEdit" type="button" class="voucher-catalog__delete-nominal" :disabled="saving" :aria-label="`Удалить номинал ${nominal.name}`" title="Удалить номинал" @click="$emit('delete')"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M3 5h14M7 5V3h6v2M5 5l1 12h8l1-12M8 8v6M12 8v6" /></svg></button>
    </div>
    <div v-if="expanded && offers.length" :id="detailsId" class="catalog-nominal__details" role="region" :aria-label="`Поставщики ${nominal.name}`">
      <div class="catalog-nominal__columns" aria-hidden="true"><span>Поставщики · по приоритету</span><span>Закупочная цена</span><span>Остаток, шт.</span><span></span></div>
      <ol class="catalog-nominal__offers">
        <li v-for="(offer, index) in offers" :key="offer.offer_id" class="catalog-nominal__offer" :class="{ 'is-disabled': offer.fulfillment_enabled === false }" :data-offer-id="offer.offer_id">
          <div class="catalog-nominal__supplier">
            <span class="catalog-nominal__rank" :aria-label="`Приоритет ${index + 1}`">{{ index + 1 }}</span>
            <div><strong>{{ offer.supplier_name }}</strong><span v-if="offer.fulfillment_enabled === false" class="catalog-nominal__disabled-label muted">Выключен</span><span class="catalog-nominal__binding muted">{{ offer.service_title }} · {{ offer.nominal_title }}</span></div>
          </div>
          <WorkVoucherCatalogSnapshot class="catalog-nominal__price" :offer="offer" kind="price" :now="now" />
          <WorkVoucherCatalogSnapshot class="catalog-nominal__stock" :offer="offer" kind="stock" :now="now" />
          <div v-if="canEdit" class="catalog-nominal__actions">
            <template v-if="unlinkOfferId === offer.offer_id"><span class="muted">Убрать связку?</span><div><button type="button" class="catalog-nominal__action" :disabled="saving" @click="confirmUnlink(offer.offer_id)">Да</button><button type="button" class="catalog-nominal__action" :disabled="saving" @click="unlinkOfferId = null">Отмена</button></div></template>
            <button v-else type="button" class="catalog-nominal__action" :disabled="saving" @click="unlinkOfferId = offer.offer_id">Отвязать</button>
          </div>
        </li>
      </ol>
      <button v-if="canEdit" type="button" class="catalog-nominal__configure" :disabled="saving" @click="$emit('edit')">Настроить поставщиков</button>
    </div>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import WorkVoucherCatalogSnapshot from './WorkVoucherCatalogSnapshot.vue'
const props = defineProps({ nominal: { type: Object, required: true }, canEdit: Boolean, saving: Boolean, now: { type: Number, required: true }, search: { type: String, default: '' } })
const emit = defineEmits(['edit', 'delete', 'unlink'])
const expanded = ref(false)
const unlinkOfferId = ref(null)
const detailsId = computed(() => `catalog-nominal-suppliers-${props.nominal.catalog_nominal_id}`)
const offers = computed(() => {
  // Порядок одинаков для сводки и деталей, включая выключенные предложения на своих местах.
  return [...props.nominal.offers].sort((a, b) => (a.fulfillment_priority ?? a.offer_id) - (b.fulfillment_priority ?? b.offer_id) || a.offer_id - b.offer_id)
})
const firstOffer = computed(() => offers.value.find((offer) => offer.fulfillment_enabled !== false) || null)
const supplierCount = computed(() => {
  // Подпись считает поставщиков, даже если один поставщик имеет несколько соответствий.
  const count = new Set(offers.value.map((offer) => offer.supplier_code)).size
  const remainder = count % 100
  const word = remainder >= 11 && remainder <= 14 ? 'поставщиков' : count % 10 === 1 ? 'поставщик' : count % 10 >= 2 && count % 10 <= 4 ? 'поставщика' : 'поставщиков'
  return `${count} ${word}`
})
watch(() => props.search, (search) => {
  // Поиск по SKU или названию раскрывает нужный номинал, не запрещая ручное сворачивание.
  const query = search.trim().toLocaleLowerCase('ru')
  if (query && [props.nominal.name, props.nominal.sku || '', ...offers.value.flatMap((offer) => [offer.service_title, offer.nominal_title, offer.supplier_name])]
    .some((value) => String(value).toLocaleLowerCase('ru').includes(query))) expanded.value = true
}, { immediate: true })

function confirmUnlink(offerId) {
  // Подтверждение относится только к одному поставщику внутри этого номинала.
  if (props.saving) return
  emit('unlink', offerId)
  unlinkOfferId.value = null
}
</script>

<style scoped>
.catalog-nominal { border-top: 1px solid var(--catalog-line); }
.catalog-nominal__summary { display: grid; grid-template-columns: minmax(150px, 1.1fr) minmax(140px, 1fr) minmax(120px, .7fr) minmax(100px, .55fr) 28px; align-items: center; gap: 16px; padding: 13px 14px; }
.catalog-nominal__identity { display: flex; gap: 10px; align-items: center; min-width: 0; }
.catalog-nominal__name { min-width: 0; display: grid; justify-items: start; gap: 5px; font-size: 13px; }
.voucher-catalog__nominal { border: 0; padding: 0; background: none; color: var(--ink); font: inherit; font-weight: 650; text-align: left; text-underline-offset: 4px; cursor: pointer; overflow-wrap: anywhere; }
.voucher-catalog__nominal:hover { color: var(--catalog-accent); text-decoration: underline; }
.catalog-nominal__count { font-size: 11px; }
.catalog-nominal__sku { color: var(--muted); font-size: 11px; font-family: ui-monospace, monospace; font-variant-numeric: tabular-nums; user-select: all; }
.catalog-nominal__expand, .voucher-catalog__delete-nominal { flex: 0 0 auto; display: grid; place-items: center; width: 28px; height: 28px; padding: 5px; border: 0; border-radius: 6px; background: transparent; color: var(--muted); cursor: pointer; }
.catalog-nominal svg { width: 16px; height: 16px; fill: none; stroke: currentColor; stroke-width: 1.6; stroke-linecap: round; stroke-linejoin: round; }
.catalog-nominal__expand svg { transition: transform .15s; }
.is-open .catalog-nominal__expand svg { transform: rotate(90deg); }
.catalog-nominal__expand:hover { background: rgba(128,148,180,.08); color: var(--ink); }
.voucher-catalog__delete-nominal:hover { color: #f29aa5; background: rgba(242,154,165,.08); }
.catalog-nominal__first { min-width: 0; display: grid; gap: 5px; justify-items: start; font-size: 12px; }
.catalog-nominal__first strong { font-weight: 600; overflow-wrap: anywhere; }
.catalog-nominal__first > span { font-size: 11px; }
.catalog-nominal__details { margin: 0 14px 14px 27px; padding: 0 0 0 13px; border-left: 2px solid rgba(84,213,173,.22); }
.catalog-nominal__columns, .catalog-nominal__offer { display: grid; grid-template-columns: minmax(190px, 1fr) minmax(120px, .55fr) minmax(100px, .4fr) 96px; gap: 16px; }
.catalog-nominal__columns { padding: 8px 10px; color: var(--muted); font-size: 10px; border-radius: 7px 7px 0 0; background: rgba(128,148,180,.045); }
.catalog-nominal__columns > span:nth-child(2), .catalog-nominal__columns > span:nth-child(3) { text-align: right; }
.catalog-nominal__offers { list-style: none; padding: 0; margin: 0; }
.catalog-nominal__offer { align-items: start; padding: 12px 10px; border-bottom: 1px solid var(--catalog-line); }
.catalog-nominal__offer.is-disabled { background: rgba(128,148,180,.025); }
.catalog-nominal__offer.is-disabled .catalog-nominal__supplier { opacity: .55; }
.catalog-nominal__supplier { display: flex; gap: 9px; min-width: 0; font-size: 12px; }
.catalog-nominal__supplier > div { min-width: 0; overflow-wrap: anywhere; }
.catalog-nominal__supplier strong { font-weight: 600; }
.catalog-nominal__rank { flex: 0 0 22px; height: 22px; display: grid; place-items: center; border-radius: 5px; color: var(--catalog-accent); background: rgba(84,213,173,.09); font-size: 11px; font-variant-numeric: tabular-nums; }
.is-disabled .catalog-nominal__rank { color: var(--muted); background: rgba(128,148,180,.08); }
.catalog-nominal__binding { display: block; margin-top: 5px; font-size: 11px; line-height: 1.4; }
.catalog-nominal__disabled-label { margin-left: 6px; font-size: 10px; }
.catalog-nominal__actions { text-align: right; font-size: 11px; }
.catalog-nominal__actions > div { display: flex; justify-content: flex-end; }
.catalog-nominal__action, .catalog-nominal__configure { border: 0; border-radius: 6px; padding: 4px 6px; background: transparent; color: var(--muted); font: inherit; font-size: 11px; cursor: pointer; }
.catalog-nominal__action:hover { color: var(--ink); background: rgba(128,148,180,.08); }
.catalog-nominal__configure { margin-top: 8px; color: var(--catalog-accent); }
.catalog-nominal button:disabled { opacity: .4; cursor: default; }
.catalog-nominal button:focus-visible { outline: 2px solid var(--catalog-accent); outline-offset: 3px; }
@media (max-width: 760px) {
  .catalog-nominal__summary { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) 28px; gap: 12px; padding: 12px; }
  .catalog-nominal__identity { grid-column: 1 / 3; }
  .voucher-catalog__delete-nominal { grid-column: 3; grid-row: 1; }
  .catalog-nominal__first { grid-column: 1 / -1; padding-left: 38px; }
  .catalog-nominal__summary > .catalog-nominal__price { grid-column: 1; padding-left: 38px; justify-items: start; text-align: left; }
  .catalog-nominal__summary > .catalog-nominal__stock { grid-column: 2; }
  .catalog-nominal__details { margin-left: 25px; margin-right: 12px; padding-left: 8px; }
  .catalog-nominal__columns { display: none; }
  .catalog-nominal__offer { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 10px; padding: 12px 8px; }
  .catalog-nominal__supplier { grid-column: 1; }
  .catalog-nominal__actions { grid-column: 2; grid-row: 1; }
  .catalog-nominal__offer > .catalog-nominal__price { grid-column: 1; grid-row: 2; justify-items: start; text-align: left; }
  .catalog-nominal__offer > .catalog-nominal__stock { grid-column: 2; grid-row: 2; }
}
@media (prefers-reduced-motion: reduce) { .catalog-nominal__expand svg { transition: none; } }
</style>
