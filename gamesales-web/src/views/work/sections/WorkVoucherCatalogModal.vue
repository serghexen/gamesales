<template>
  <teleport to="body">
    <div v-if="ctx.formOpen" class="work-page work-modal-root modal-backdrop" @click.self="requestClose" @keydown="onKeydown">
      <div ref="modalRef" class="modal modal--auto voucher-catalog-editor" :class="{ 'is-confirming': confirmOpen }" :style="modalStyle" :role="confirmOpen ? 'alertdialog' : 'dialog'" aria-modal="true" :aria-labelledby="confirmOpen ? 'voucher-catalog-confirm-title' : 'voucher-catalog-editor-title'" :aria-busy="ctx.saving">
        <div class="voucher-catalog-editor__content" :inert="confirmOpen ? true : undefined" :aria-hidden="confirmOpen || undefined">
          <div class="panel__head panel__head--tight modal__head" @mousedown="dragHeader">
            <div class="voucher-catalog-editor__heading">
              <h3 id="voucher-catalog-editor-title">{{ ctx.title }}</h3>
              <p v-if="ctx.mode !== 'service' && ctx.draft.name" class="voucher-catalog-editor__parent">{{ ctx.draft.name }}</p>
              <p v-if="ctx.mode === 'nominal' && ctx.draft.sku" class="voucher-catalog-editor__sku">SKU {{ ctx.draft.sku }}</p>
            </div>
            <div class="toolbar-actions voucher-catalog-editor__actions">
              <button class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--save voucher-catalog-editor__save" type="submit" form="voucher-catalog-editor-form" :disabled="ctx.saving || ctx.optionsLoading" :aria-label="saveLabel" :title="saveLabel">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h12l4 4v12H4z" /><path d="M7 4v6h8V4M7 20v-6h10v6" /></svg>
              </button>
              <button v-if="ctx.mode === 'nominal' || (ctx.mode === 'service' && ctx.draft.item_id)" type="button" class="btn btn--icon-plain deal-create-action-btn deal-create-action-btn--delete voucher-catalog-editor__delete" :disabled="ctx.saving" :aria-label="ctx.mode === 'service' ? 'Удалить услугу' : 'Удалить номинал'" :title="ctx.mode === 'service' ? 'Удалить услугу' : 'Удалить номинал'" @click="askDelete">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 6h14M9 6V4h6v2M7 6l1 14h8l1-14" /></svg>
              </button>
              <button class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--close" type="button" :disabled="ctx.saving" aria-label="Закрыть" title="Закрыть · Esc" @click="requestClose">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6l-12 12" /></svg>
              </button>
            </div>
          </div>
          <form id="voucher-catalog-editor-form" class="modal__body" @submit.prevent="ctx.save">
            <fieldset :disabled="ctx.saving" class="voucher-catalog-editor__fields">
              <label v-if="ctx.mode === 'service'" class="field"><span class="label">Название услуги</span>
                <input v-model="ctx.draft.name" class="input" maxlength="250" required placeholder="Например, PlayStation — Turkey" data-test="catalog-name">
              </label>
              <div v-if="ctx.mode === 'nominals'" class="voucher-catalog-editor__tabs" aria-label="Способ добавления">
                <button type="button" :class="{ active: ctx.draft.source === 'supplier' }" :aria-pressed="ctx.draft.source === 'supplier'" @click="ctx.draft.source = 'supplier'">Выбрать у поставщика</button>
                <button type="button" :class="{ active: ctx.draft.source === 'manual' }" :aria-pressed="ctx.draft.source === 'manual'" @click="ctx.draft.source = 'manual'">Добавить вручную</button>
              </div>
              <label v-if="ctx.mode === 'nominal' || (ctx.mode === 'nominals' && ctx.draft.source === 'manual')" class="field">
                <span class="label">Наш номинал</span><input v-model="ctx.draft.nominal_name" class="input" maxlength="250" required placeholder="Например, 1000 TRY" data-test="catalog-own-nominal">
              </label>
              <template v-if="ctx.mode === 'nominal'">
                <WorkVoucherCatalogRouting :offers="ctx.draft.routing_offers" :disabled="ctx.saving" @move="ctx.moveOffer" @toggle="ctx.toggleOffer" />
                <div class="voucher-catalog-editor__binding-action">
                  <button v-if="!ctx.bindingOpen" type="button" class="ghost" @click="ctx.showBinding">+ Связать поставщика</button>
                  <template v-else><span class="muted voucher-catalog-editor__hint">Новая связка добавится в конец списка.</span><button type="button" class="ghost" @click="ctx.hideBinding">Отменить новую связку</button></template>
                </div>
              </template>
              <template v-if="(!ctx.draft.item_id || ctx.mode !== 'service') && !(ctx.mode === 'nominals' && ctx.draft.source === 'manual') && (ctx.mode !== 'nominal' || ctx.bindingOpen)">
                <p class="muted voucher-catalog-editor__hint">{{ ctx.mode === 'nominal' ? 'Можно добавить соответствие у поставщика.' : 'Отметьте нужные номиналы. Свои названия можно изменить справа.' }}</p>
                <div class="voucher-catalog-editor__supplier">
                  <label class="field"><span class="label">Поставщик</span>
                    <WorkVoucherSelect v-model="ctx.draft.supplier_code" :options="ctx.availableSuppliers" :disabled="ctx.saving" @change="ctx.loadOptions" />
                  </label>
                  <label v-if="ctx.draft.supplier_code !== 'warehouse'" class="field"><span class="label">Услуга поставщика</span>
                    <WorkVoucherSelect v-model="ctx.draft.service_id" label="Услуга поставщика" placeholder="Выберите услугу" :options="serviceOptions"
                      :disabled="ctx.optionsLoading || ctx.saving" data-test="catalog-service" @change="ctx.selectService" />
                  </label>
                </div>
                <div v-if="ctx.draft.supplier_code === 'warehouse'" class="voucher-catalog-editor__warehouse" aria-live="polite">
                  <div><strong>Собственные ключи</strong><small class="muted">{{ ctx.draft.sku }} · {{ ctx.draft.nominal_name }}</small></div>
                  <span v-if="ctx.optionsLoading" class="muted">Загружаем остаток…</span>
                  <template v-else-if="ctx.warehousePreview">
                    <div><small class="muted">Цена пула</small><strong>{{ warehousePrice }}</strong></div>
                    <div><small class="muted">Свободно</small><strong>{{ ctx.warehousePreview.free_count }} шт.</strong></div>
                  </template>
                </div>
                <label v-else-if="ctx.mode === 'nominal' && ctx.draft.service_id" class="field"><span class="label">Номинал поставщика</span>
                  <select v-model="ctx.draft.link_nominal_id" class="input input--select" data-test="catalog-link-nominal">
                    <option value="">Выберите номинал</option>
                    <option v-for="nominal in ctx.nominals" :key="nominal.nominal_id" :value="String(nominal.nominal_id)" :disabled="nominal.linked">{{ nominal.nominal_title }}{{ nominal.linked ? ' · уже связан' : '' }}</option>
                  </select>
                </label>
                <div v-else-if="ctx.draft.service_id" class="voucher-catalog-editor__nominals">
                  <div class="voucher-catalog-editor__selection">
                    <strong>Номиналы <span class="voucher-catalog-editor__count">{{ ctx.draft.selected.length }} / {{ ctx.nominals.length }}</span></strong>
                    <div class="toolbar-actions"><button type="button" class="voucher-catalog-editor__text-action" @click="ctx.selectAll(true)">Выбрать все</button><button type="button" class="voucher-catalog-editor__text-action" :disabled="!ctx.draft.selected.length" @click="ctx.selectAll(false)">Снять выбор</button></div>
                  </div>
                  <div class="voucher-catalog-editor__columns" aria-hidden="true"><span>У поставщика</span><span>Наше название</span></div>
                  <div class="voucher-catalog-editor__list" role="group" aria-label="Номиналы поставщика">
                    <div v-for="option in ctx.nominals" :key="option.nominal_id" class="voucher-catalog-editor__option" :class="{ 'is-linked': option.linked, 'is-selected': Boolean(selected(option.nominal_id)) }">
                      <label class="voucher-catalog-editor__check">
                        <input type="checkbox" :checked="Boolean(selected(option.nominal_id))" :disabled="option.linked" :data-test="`catalog-select-${option.nominal_id}`" @change="ctx.toggleNominal(option, $event.target.checked)">
                        <span>{{ option.nominal_title }}</span>
                      </label>
                      <input v-if="selected(option.nominal_id)" v-model="selected(option.nominal_id).name" class="input" maxlength="250" required :aria-label="`Наше название для ${option.nominal_title}`">
                      <span v-else class="voucher-catalog-editor__row-hint muted">{{ option.linked ? 'Уже в услуге' : '—' }}</span>
                    </div>
                    <p v-if="!ctx.nominals.length" class="muted voucher-catalog-editor__empty">Нет доступных номиналов.</p>
                  </div>
                </div>
                <p v-if="ctx.mode === 'service'" class="muted voucher-catalog-editor__hint">Номиналы можно добавить позже.</p>
              </template>
            </fieldset>
            <p v-if="ctx.formError" class="bad voucher-catalog-editor__error" role="alert">{{ ctx.formError }} <button v-if="!ctx.optionsLoading && !ctx.services.length && (!ctx.draft.item_id || ctx.mode === 'nominals' || ctx.bindingOpen)" class="ghost" type="button" :disabled="ctx.saving" @click="ctx.loadOptions">Повторить загрузку</button></p>
          </form>
          <div v-if="ctx.saving || ctx.draft.selected.length || ctx.draft.link_nominal_id" class="voucher-catalog-editor__footer">
            <p class="muted voucher-catalog-editor__hint" :role="ctx.saving ? 'status' : undefined">{{ ctx.draft.supplier_code === 'warehouse' ? 'Склад добавится в приоритет поставщиков после сохранения карточки.' : ctx.saving ? 'Сохраняем, получаем цены и остатки…' : 'При сохранении загрузим цены и остатки.' }}</p>
          </div>
        </div>
        <div v-if="confirmOpen" ref="confirmRef" class="voucher-catalog-editor__confirm" :class="{ 'voucher-catalog-editor__confirm--unsaved': !ctx.deleteConfirm }">
          <div :class="ctx.deleteConfirm ? 'voucher-catalog-editor__confirm-card' : 'modal modal--auto unsaved-confirm__modal'">
            <template v-if="ctx.deleteConfirm">
              <h3 id="voucher-catalog-confirm-title">{{ ctx.mode === 'service' ? `Удалить услугу «${ctx.deleteServiceName}»?` : `Удалить номинал «${ctx.draft.nominal_name}»?` }}</h3>
              <p v-if="ctx.mode === 'service'" class="muted">Будут удалены услуга, все её номиналы ({{ ctx.deleteServiceNominalCount }}) и их связки с поставщиками. Отменить удаление нельзя.</p>
              <p v-else class="muted">Номинал и все его связки с поставщиками будут удалены. Остальные номиналы услуги останутся. Отменить удаление нельзя.</p>
              <p v-if="ctx.formError" class="bad" role="alert">{{ ctx.formError }}</p>
              <div class="toolbar-actions"><button type="button" class="btn catalog-modal-action catalog-modal-action--text catalog-modal-action--close" :disabled="ctx.saving" @click="ctx.deleteConfirm = false">{{ ctx.mode === 'service' ? 'Оставить услугу' : 'Оставить номинал' }}</button><button type="button" class="ghost voucher-catalog-editor__delete catalog-modal-action catalog-modal-action--text catalog-modal-action--delete" :disabled="ctx.saving" @click="ctx.mode === 'service' ? ctx.deleteService() : ctx.deleteNominal()">{{ ctx.saving ? 'Удаляем…' : ctx.mode === 'service' ? 'Удалить услугу' : 'Удалить номинал' }}</button></div>
            </template>
            <template v-else>
              <div class="panel__head panel__head--tight unsaved-confirm__head">
                <h3 id="voucher-catalog-confirm-title" class="unsaved-confirm__title">Несохраненные изменения</h3>
              </div>
              <div class="modal__body">
                <p class="muted unsaved-confirm__text">Закрыть без сохранения?</p>
                <div class="toolbar-actions unsaved-confirm__actions">
                  <button type="button" class="ghost" @click="ctx.closeConfirm = false">Остаться</button>
                  <button type="button" class="btn btn--danger" @click="ctx.discard">Закрыть</button>
                </div>
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useModalDrag } from '../useModalDrag'
import WorkVoucherCatalogRouting from './WorkVoucherCatalogRouting.vue'
import WorkVoucherSelect from './WorkVoucherSelect.vue'
const props = defineProps({ ctx: { type: Object, required: true } })
const { modalRef, modalStyle, startModalDrag, stopModalDrag, resetModalPos } = useModalDrag()
const serviceOptions = computed(() => {
  // Общее меню сохраняет возможность сбросить услугу и связанные номиналы.
  return [{ code: '', name: props.ctx.optionsLoading ? 'Загрузка услуг…' : 'Выберите услугу' },
    ...props.ctx.services.map((service) => ({ code: String(service.id), name: service.title }))]
})
const warehousePrice = computed(() => {
  // Не подменяем отсутствующую цену нулём в предпросмотре склада.
  const value = props.ctx.warehousePreview?.price
  return value == null ? 'Не задана' : new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB' }).format(Number(value))
})
const confirmRef = ref(null)
const confirmOpen = computed(() => props.ctx.closeConfirm || props.ctx.deleteConfirm)
const saveLabel = computed(() => {
  // Подпись и подсказка сохраняют смысл действия, когда вместо текста показана иконка.
  const ctx = props.ctx
  if (ctx.saving) return 'Сохраняем…'
  return ctx.mode === 'nominals'
    ? `Добавить${ctx.draft.source === 'supplier' && ctx.draft.selected.length ? ` · ${ctx.draft.selected.length}` : ''}`
    : 'Сохранить'
})
let previousFocus = null
let editingFocus = null
let previousOverflow = null

function selected(id) {
  // Находим собственную подпись в выбранном пакете, не меняя данные поставщика.
  return props.ctx.draft.selected.find((item) => item.id === String(id))
}

function dragHeader(event) {
  // Действия в шапке не должны начинать перетаскивание окна.
  if (!event.target.closest('button')) startModalDrag(event)
}

function requestClose() {
  // Запоминаем фокус до скрытия полей: inert может сразу перенести его на body.
  if (props.ctx.saving) return
  if (props.ctx.deleteConfirm) { props.ctx.deleteConfirm = false; return }
  if (!confirmOpen.value) editingFocus = document.activeElement
  props.ctx.requestClose()
}

function askDelete() {
  // Возвращаем фокус кнопке удаления, если пользователь передумает в подтверждении.
  editingFocus = document.activeElement
  if (props.ctx.mode === 'service') props.ctx.askDeleteService()
  else props.ctx.askDelete()
}

function onKeydown(event) {
  // Escape возвращает из подтверждения в форму; Tab не выпускает фокус в скрытые поля.
  if (event.key === 'Escape') {
    event.preventDefault()
    event.stopPropagation()
    if (props.ctx.saving) return
    if (props.ctx.deleteConfirm) props.ctx.deleteConfirm = false
    else if (props.ctx.closeConfirm) props.ctx.closeConfirm = false
    else requestClose()
    return
  }
  if (event.key !== 'Tab') return
  const scope = confirmOpen.value ? confirmRef.value : modalRef.value
  const controls = [...scope.querySelectorAll('button:not(:disabled), input:not(:disabled), select:not(:disabled)')]
    .filter((element) => !element.closest('fieldset[disabled]'))
  const first = controls[0], last = controls[controls.length - 1]
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
}

function releaseModal() {
  // Возвращаем прокрутку страницы и фокус кнопке, открывшей карточку.
  stopModalDrag()
  if (previousOverflow !== null) document.body.style.overflow = previousOverflow
  previousOverflow = null
  if (!props.ctx.saving) previousFocus?.focus?.()
}

watch(confirmOpen, async (confirm) => {
  // Подтверждение находится поверх списка и получает фокус независимо от его прокрутки.
  await nextTick()
  if (confirm) confirmRef.value?.querySelector('button')?.focus()
  else if (props.ctx.formOpen) {
    const fallback = modalRef.value?.querySelector('input:not(:disabled), button:not(:disabled)')
    const target = editingFocus?.isConnected ? editingFocus : fallback
    target?.focus()
  }
})
watch(() => props.ctx.formOpen, async (open) => {
  // Каждое открытие начинается по центру экрана и сразу позволяет заполнять форму.
  if (!open) { releaseModal(); return }
  previousFocus = document.activeElement
  previousOverflow = document.body.style.overflow
  document.body.style.overflow = 'hidden'
  resetModalPos()
  await nextTick()
  if (!confirmOpen.value) modalRef.value?.querySelector('input:not(:disabled), select:not(:disabled)')?.focus()
}, { immediate: true })
watch(() => props.ctx.saving, async (saving) => {
  // После сохранения кнопка открытия снова доступна; теперь можно вернуть ей фокус.
  if (!saving && !props.ctx.formOpen) {
    await nextTick()
    if (previousFocus?.isConnected && previousFocus !== document.body) previousFocus.focus()
    else document.querySelector('.voucher-catalog input[type="search"]')?.focus()
  }
})
onBeforeUnmount(releaseModal)
</script>

<style scoped>
/* Область окна переопределяет размеры общих модалок, не затрагивая сделки и аккаунты. */
.work-modal-root.modal-backdrop .voucher-catalog-editor.modal {
  position: relative; width: min(780px, calc(100vw - 32px)); height: auto;
  max-height: calc(100dvh - 40px); padding: 0; border-radius: 18px;
}
.voucher-catalog-editor__content { display: flex; flex-direction: column; min-height: 0; }
.work-modal-root.modal-backdrop .voucher-catalog-editor.is-confirming { min-height: min(320px, calc(100dvh - 40px)); }
.work-modal-root.modal-backdrop .voucher-catalog-editor .modal__head {
  flex: 0 0 auto; display: flex; align-items: center; justify-content: space-between;
  gap: 16px; padding: 18px 20px 14px; margin: 0; border-bottom: 1px solid var(--stroke);
}
.voucher-catalog-editor__heading { min-width: 0; }
.work-modal-root .voucher-catalog-editor h3:not(.unsaved-confirm__title) { margin: 0; font-size: 15px; font-weight: 650; line-height: 1.4; text-transform: none; letter-spacing: 0; }
.voucher-catalog-editor__parent { margin: 3px 0 0; font-size: 13px; color: var(--muted); overflow-wrap: anywhere; }
.voucher-catalog-editor__sku { margin: 4px 0 0; color: var(--muted); font-size: 11px; font-family: ui-monospace, monospace; user-select: all; }
.work-modal-root.modal-backdrop .voucher-catalog-editor.modal--auto > .voucher-catalog-editor__content > .modal__body { padding: 16px 20px; overflow-y: auto; min-height: 0; max-height: none; }
.voucher-catalog-editor__fields { display: grid; gap: 12px; border: 0; padding: 0; margin: 0; min-width: 0; }
.voucher-catalog-editor__binding-action { display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; }
.work-modal-root .voucher-catalog-editor .field { margin: 0; gap: 5px; }
.work-modal-root .voucher-catalog-editor .input { height: 36px; min-width: 0; padding: 0 10px; border-radius: 8px; font-size: 13px; }
.work-modal-root .voucher-catalog-editor .input:focus-visible { outline: 2px solid #52cea7; outline-offset: 1px; }
.voucher-catalog-editor__warehouse { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; padding: 12px 14px; border: 1px solid var(--stroke); border-radius: 10px; background: rgba(128,148,180,.035); font-size: 13px; }
.voucher-catalog-editor__warehouse > div { display: grid; gap: 4px; }
.voucher-catalog-editor__warehouse > div:not(:first-child) { text-align: right; }
.voucher-catalog-editor__warehouse small { font-size: 11px; }
.voucher-catalog-editor__supplier { display: grid; grid-template-columns: 160px minmax(0, 1fr); gap: 12px; }
.voucher-catalog-editor__tabs { display: flex; gap: 3px; padding: 3px; border: 1px solid var(--stroke); border-radius: 10px; width: fit-content; background: rgba(0,0,0,.12); }
.voucher-catalog-editor__tabs button { padding: 7px 12px; border: 0; border-radius: 7px; background: transparent; color: var(--muted); font-size: 12px; font-weight: 600; cursor: pointer; }
.voucher-catalog-editor__tabs button.active { color: #91e3c7; background: rgba(64,198,152,.14); box-shadow: inset 0 0 0 1px rgba(100,215,175,.17); }
.voucher-catalog-editor__hint { margin: 0; font-size: 12px; line-height: 1.5; }
.voucher-catalog-editor__selection { display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; margin: 2px 0 8px; font-size: 13px; }
.voucher-catalog-editor__count { display: inline-block; margin-left: 6px; padding: 2px 6px; background: rgba(64,198,152,.12); border-radius: 5px; color: #91e3c7; font-size: 11px; font-variant-numeric: tabular-nums; }
.voucher-catalog-editor__text-action { border: 0; padding: 3px 0; background: none; color: var(--muted); font-size: 12px; cursor: pointer; }
.voucher-catalog-editor__text-action:hover { color: var(--ink); }
.voucher-catalog-editor button:disabled { opacity: .45; cursor: default; }
.voucher-catalog-editor button:focus-visible { outline: 2px solid #52cea7; outline-offset: 2px; }
.voucher-catalog-editor__columns, .voucher-catalog-editor__option { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 16px; padding: 5px 12px; align-items: center; }
.voucher-catalog-editor__columns { padding-top: 7px; padding-bottom: 7px; color: var(--muted); font-size: 11px; border: 1px solid var(--stroke); border-bottom: 0; border-radius: 10px 10px 0 0; background: rgba(255,255,255,.035); }
.voucher-catalog-editor__list { max-height: min(320px, 42dvh); overflow-y: auto; overscroll-behavior: contain; border: 1px solid var(--stroke); border-radius: 0 0 10px 10px; scrollbar-width: thin; }
.voucher-catalog-editor__option { min-height: 44px; border-bottom: 1px solid var(--stroke); }
.voucher-catalog-editor__option:last-child { border-bottom: 0; }
.voucher-catalog-editor__option.is-selected { background: rgba(64,198,152,.055); }
.voucher-catalog-editor__option.is-linked { opacity: .6; }
.voucher-catalog-editor__check { display: flex; align-items: center; gap: 10px; cursor: pointer; min-height: 32px; font-size: 13px; overflow-wrap: anywhere; }
.voucher-catalog-editor__check input { flex: 0 0 16px; width: 16px; height: 16px; margin: 0; accent-color: #52cea7; }
.work-modal-root .voucher-catalog-editor__option .input { height: 32px; }
.voucher-catalog-editor__row-hint { font-size: 12px; }
.voucher-catalog-editor__empty { padding: 12px; margin: 0; font-size: 13px; }
.voucher-catalog-editor__footer { display: flex; flex: 0 0 auto; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 20px; border-top: 1px solid var(--stroke); background: rgba(255,255,255,.02); }
.voucher-catalog-editor__actions { flex: 0 0 auto; }
.voucher-catalog-editor .toolbar-actions:not(.unsaved-confirm__actions) { display: flex; align-items: center; gap: 12px; }
.work-modal-root .voucher-catalog-editor__content .btn:not(.catalog-modal-action):not(.deal-create-action-btn), .work-modal-root .voucher-catalog-editor__content .ghost:not(.catalog-modal-action) { min-height: 34px; padding: 7px 12px; border-radius: 9px; font-size: 12px; line-height: 1.4; }
.voucher-catalog-editor__error { margin: 12px 0 0; font-size: 13px; overflow-wrap: anywhere; }
.voucher-catalog-editor__confirm { position: absolute; inset: 0; z-index: 2; display: flex; align-items: center; justify-content: center; padding: 20px; background: rgba(6,10,20,.86); backdrop-filter: blur(5px); overflow-y: auto; }
.voucher-catalog-editor__confirm-card { width: 100%; max-width: 440px; padding: 20px; border: 1px solid var(--stroke); border-radius: 14px; background: var(--modal-bg, #101727); box-shadow: 0 12px 36px rgba(0,0,0,.3); }
.voucher-catalog-editor__confirm-card p { font-size: 13px; line-height: 1.5; margin: 10px 0 18px; }
.voucher-catalog-editor__confirm-card .toolbar-actions { flex-wrap: wrap; gap: 8px; }
/* Системная настройка уменьшения движения убирает блик и подъём, сохраняя цвета действий. */
@media (prefers-reduced-motion: reduce) {
  .work-modal-root.modal-backdrop .voucher-catalog-editor .catalog-modal-action { transition: none; }
  .work-modal-root.modal-backdrop .voucher-catalog-editor .catalog-modal-action::before { display: none; }
  .work-modal-root.modal-backdrop .voucher-catalog-editor .catalog-modal-action:not(:disabled):hover,
  .work-modal-root.modal-backdrop .voucher-catalog-editor .catalog-modal-action:not(:disabled):active { transform: none; }
}
@media (max-width: 580px) {
  .work-modal-root.modal-backdrop .voucher-catalog-editor.modal { width: calc(100vw - 16px); max-height: calc(100dvh - 16px); }
  .work-modal-root.modal-backdrop .voucher-catalog-editor .modal__head { padding: 14px; }
  .work-modal-root.modal-backdrop .voucher-catalog-editor.modal--auto > .voucher-catalog-editor__content > .modal__body { padding: 14px; }
  .voucher-catalog-editor__supplier { grid-template-columns: 1fr; gap: 10px; }
  .voucher-catalog-editor__footer { padding: 12px 14px; flex-wrap: wrap; }
  .voucher-catalog-editor__tabs { width: 100%; }
  .voucher-catalog-editor__tabs button { flex: 1; padding: 7px; }
  .voucher-catalog-editor__columns, .voucher-catalog-editor__option { gap: 10px; padding-left: 8px; padding-right: 8px; }
}
</style>
