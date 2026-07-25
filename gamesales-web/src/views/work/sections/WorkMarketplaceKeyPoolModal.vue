<template>
  <teleport to="body">
    <div v-if="showMarketplaceKeyPool" class="work-page work-modal-root modal-backdrop marketplace-key-pool-backdrop" @click.self="closeMarketplaceKeyPool">
      <div class="modal modal--auto marketplace-key-pool-modal marketplace-key-pool-modal--add-only">
        <div class="panel__head panel__head--tight modal__head">
          <div><h3>Добавить ключи · {{ marketplaceLabel }}</h3><p>{{ marketplaceKeyPool.product_title || marketplaceKeyPool.product_key }}</p></div>
          <div class="toolbar-actions ozon-digital-modal__head-actions">
            <button class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--save" type="button" :disabled="marketplaceKeyPoolSaving" title="Сохранить ключи" aria-label="Сохранить ключи" @click="submitKeys">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h12l4 4v12H4z" /><path d="M7 4v6h8V4" /><path d="M7 20v-6h10v6" /></svg>
            </button>
            <button class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--edit" type="button" title="К настройкам ключей" aria-label="К настройкам ключей" @click="closeMarketplaceKeyPool"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 12H5" /><path d="m11 18-6-6 6-6" /></svg></button>
            <button class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--close" type="button" title="Закрыть" aria-label="Закрыть" @click="closeMarketplaceKeyPool"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6l-12 12" /></svg></button>
          </div>
        </div>
        <div class="modal__body marketplace-key-pool-modal__body" :class="{ 'modal__body--locked': marketplaceKeyPoolLoading || marketplaceKeyPoolSaving, 'modal__body--loader': marketplaceKeyPoolSaving }">
          <div v-if="marketplaceKeyPoolSaving" class="modal__body-overlay"><WorkHamsterLoader label="Сохраняем ключи…" /></div>
          <p v-if="marketplaceKeyPoolError" class="bad">{{ marketplaceKeyPoolError }}</p>
          <p v-if="marketplaceKeyPoolOk" class="good">{{ marketplaceKeyPoolOk }}</p>
          <section class="marketplace-key-pool-modal__add">
            <label class="field"><textarea v-model="draftCodes" class="input textarea" rows="5" aria-label="Ключи" placeholder="Каждый ключ с новой строки"></textarea></label>
            <div class="field marketplace-key-pool-modal__expiry">
              <span>Активировать до</span>
              <div class="marketplace-key-pool-modal__expiry-controls">
                <input v-model="draftExpiresAt" class="input" type="date" />
                <div class="marketplace-key-pool-modal__expiry-shortcuts">
                  <button class="ghost" type="button" aria-label="Добавить месяц к дате" @click="shiftExpiresAt(1)">+ месяц</button>
                  <button class="ghost" type="button" aria-label="Добавить год к дате" @click="shiftExpiresAt(12)">+ год</button>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { computed, ref } from 'vue'
import WorkHamsterLoader from './WorkHamsterLoader.vue'

const props = defineProps({
  showMarketplaceKeyPool: { type: Boolean, required: true }, closeMarketplaceKeyPool: { type: Function, required: true }, marketplaceKeyPool: { type: Object, required: true }, marketplaceKeyPoolLoading: { type: Boolean, required: true }, marketplaceKeyPoolSaving: { type: Boolean, required: true }, marketplaceKeyPoolError: { type: String, default: '' }, marketplaceKeyPoolOk: { type: String, default: '' }, addMarketplaceKeyPoolKeys: { type: Function, required: true },
})
const draftCodes = ref('')
const draftExpiresAt = ref('')
const marketplaceLabel = computed(() => String(props.marketplaceKeyPool.marketplace) === 'ozon' ? 'Ozon' : 'Яндекс Маркет')

async function submitKeys() {
  // Очищает форму после сохранения, а таблица за окном обновляется из общего состояния пула.
  const result = await props.addMarketplaceKeyPoolKeys(draftCodes.value, draftExpiresAt.value)
  if (result?.ok) { draftCodes.value = ''; draftExpiresAt.value = '' }
}

function shiftExpiresAt(monthsToAdd) {
  // Сдвигает дату без переполнения конца месяца, чтобы оператор быстро задавал срок действия ключей.
  const source = /^\d{4}-\d{2}-\d{2}$/.test(draftExpiresAt.value) ? draftExpiresAt.value.split('-').map(Number) : null
  const base = source ? new Date(source[0], source[1] - 1, source[2]) : new Date()
  const day = base.getDate()
  const target = new Date(base.getFullYear(), base.getMonth() + monthsToAdd, 1)
  const lastDay = new Date(target.getFullYear(), target.getMonth() + 1, 0).getDate()
  target.setDate(Math.min(day, lastDay))
  draftExpiresAt.value = [target.getFullYear(), String(target.getMonth() + 1).padStart(2, '0'), String(target.getDate()).padStart(2, '0')].join('-')
}
</script>
