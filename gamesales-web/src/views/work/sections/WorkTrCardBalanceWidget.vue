<template>
  <section data-test="finance-tr-card-balance" class="tr-card-balance">
    <div class="tr-card-balance__summary">
      <strong class="tr-card-balance__value" :class="trCardBalanceClass">{{ formatTrCardAmount(ctx.financeTrCardBalance?.current_balance) }}</strong>
      <button
        data-test="finance-refresh-tr-card-balance"
        class="tr-card-balance__icon-btn"
        type="button"
        :disabled="ctx.financeTrCardBalanceLoading || ctx.financeTrCardBalanceSaving"
        aria-label="Обновить баланс TR-карты"
        title="Обновить баланс"
        @click="refreshTrCardBalance"
      >
        <span v-if="ctx.financeTrCardBalanceLoading" class="tr-card-balance__loader">
          <span aria-label="Обновляем баланс" role="img" class="wheel-and-hamster wheel-and-hamster--mini tr-card-balance__loader-wheel">
            <span class="wheel"></span>
            <span class="hamster">
              <span class="hamster__body">
                <span class="hamster__head">
                  <span class="hamster__ear"></span>
                  <span class="hamster__eye"></span>
                  <span class="hamster__nose"></span>
                </span>
                <span class="hamster__limb hamster__limb--fr"></span>
                <span class="hamster__limb hamster__limb--fl"></span>
                <span class="hamster__limb hamster__limb--br"></span>
                <span class="hamster__limb hamster__limb--bl"></span>
                <span class="hamster__tail"></span>
              </span>
            </span>
            <span class="spoke"></span>
          </span>
        </span>
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
          <path d="M20 12a8 8 0 1 1-2.3-5.7" />
          <path d="M20 4v6h-6" />
        </svg>
      </button>
      <button
        v-if="canEdit"
        data-test="finance-edit-tr-card-balance"
        class="tr-card-balance__icon-btn"
        type="button"
        :disabled="ctx.financeTrCardBalanceLoading || ctx.financeTrCardBalanceSaving"
        aria-label="Редактировать баланс TR-карты"
        title="Редактировать баланс"
        @click="openTrCardBalanceEdit"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
          <path d="M12 20h9" />
          <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z" />
        </svg>
      </button>
    </div>

    <teleport to="body">
      <div v-if="trCardEditOpen" class="work-page work-modal-root modal-backdrop" @click.self="closeTrCardBalanceEdit">
        <div class="modal modal--auto tr-card-balance-modal">
          <div class="panel__head panel__head--tight">
            <h3>Баланс TR-карты</h3>
          </div>
          <div class="modal__body" :class="{ 'modal__body--locked': ctx.financeTrCardBalanceSaving }">
            <div v-if="ctx.financeTrCardBalanceSaving" class="modal__body-overlay">
              <div class="loader-wrap loader-wrap--compact">
                <div aria-label="Orange and tan hamster running in a metal wheel" role="img" class="wheel-and-hamster wheel-and-hamster--mini">
                  <div class="wheel"></div>
                  <div class="hamster">
                    <div class="hamster__body">
                      <div class="hamster__head">
                        <div class="hamster__ear"></div>
                        <div class="hamster__eye"></div>
                        <div class="hamster__nose"></div>
                      </div>
                      <div class="hamster__limb hamster__limb--fr"></div>
                      <div class="hamster__limb hamster__limb--fl"></div>
                      <div class="hamster__limb hamster__limb--br"></div>
                      <div class="hamster__limb hamster__limb--bl"></div>
                      <div class="hamster__tail"></div>
                    </div>
                  </div>
                  <div class="spoke"></div>
                </div>
                <p class="muted">Сохраняем…</p>
              </div>
            </div>
            <div class="analytics-filters">
              <label class="field">
                <span class="label">Новый баланс</span>
                <input
                  v-model="ctx.financeTrCardBalanceDraft"
                  class="input"
                  type="number"
                  step="0.01"
                  aria-label="Фактический баланс TR-карты"
                />
              </label>
            </div>
            <p v-if="ctx.financeTrCardBalanceError" class="bad">{{ ctx.financeTrCardBalanceError }}</p>
            <div class="toolbar-actions">
              <button data-test="finance-cancel-tr-card-balance" class="ghost" type="button" :disabled="ctx.financeTrCardBalanceSaving" @click="closeTrCardBalanceEdit">Отмена</button>
              <button data-test="finance-save-tr-card-balance" class="ghost" type="button" :disabled="ctx.financeTrCardBalanceSaving" @click="saveTrCardBalance">
                {{ ctx.financeTrCardBalanceSaving ? 'Сохраняем...' : 'Сохранить' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </teleport>
  </section>
</template>

<script setup>
import { computed, ref, unref } from 'vue'

const props = defineProps({
  ctx: { type: Object, required: true },
})

const trCardEditOpen = ref(false)
const canEdit = computed(() => Boolean(unref(props.ctx.canManageRolePermissions)))

const trCardBalanceClass = computed(() => {
  // Подсвечиваем остаток карты по знаку, чтобы минус был заметен в шапке.
  const currentBalance = Number(props.ctx.financeTrCardBalance?.current_balance || 0)
  return currentBalance < 0 ? 'tr-card-balance__value--negative' : 'tr-card-balance__value--positive'
})

// Форматируем баланс TR отдельно от рублевых отчетов, чтобы валюта карты не смешивалась с Cash Flow.
function formatTrCardAmount(value) {
  const amount = Number(value || 0)
  const formatted = typeof props.ctx.formatPrice === 'function'
    ? props.ctx.formatPrice(amount)
    : amount.toFixed(2)
  return `${formatted} TRY`
}

// Открываем ручную установку баланса только для admin/owner.
function openTrCardBalanceEdit() {
  if (!canEdit.value) return
  props.ctx.financeTrCardBalanceDraft = String(props.ctx.financeTrCardBalance?.current_balance ?? '')
  trCardEditOpen.value = true
}

// Закрываем форму без сохранения и возвращаем черновик к текущему остатку.
function closeTrCardBalanceEdit() {
  props.ctx.financeTrCardBalanceDraft = String(props.ctx.financeTrCardBalance?.current_balance ?? '')
  trCardEditOpen.value = false
}

// Перечитываем баланс TR-карты без открытия формы редактирования.
async function refreshTrCardBalance() {
  await props.ctx.loadFinanceTrCardBalance?.()
}

// Сохраняем введенный фактический остаток TR-карты и закрываем модалку после успешного ответа.
async function saveTrCardBalance() {
  const ok = await props.ctx.saveFinanceTrCardBalance?.()
  if (ok) trCardEditOpen.value = false
}
</script>

<style scoped>
.tr-card-balance {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  min-width: 0;
  min-height: 42px;
  margin-left: 2px;
  padding: 5px 8px;
  box-sizing: border-box;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 12px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.09), rgba(255, 255, 255, 0.04)),
    rgba(8, 13, 25, 0.34);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.12),
    0 6px 18px rgba(3, 8, 20, 0.24);
}

.tr-card-balance__summary {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  min-height: 0;
}

.tr-card-balance__value {
  font-size: 15px;
  line-height: 1.15;
  white-space: nowrap;
}

.tr-card-balance__value--positive {
  color: #22c55e;
}

.tr-card-balance__value--negative {
  color: #ef4444;
}

.tr-card-balance__icon-btn {
  display: inline-grid;
  place-items: center;
  width: 24px;
  height: 24px;
  padding: 0;
  border: 1px solid rgba(148, 163, 184, 0.32);
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.42);
  color: var(--muted);
  cursor: pointer;
}

.tr-card-balance__icon-btn:hover:not(:disabled) {
  color: var(--text);
  border-color: rgba(148, 163, 184, 0.58);
}

.tr-card-balance__icon-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.tr-card-balance__icon-btn svg {
  width: 14px;
  height: 14px;
}

.tr-card-balance__loader {
  display: inline-grid;
  place-items: center;
  width: 16px;
  height: 16px;
  overflow: visible;
}

.tr-card-balance__loader-wheel.wheel-and-hamster--mini {
  width: 11.5em;
  height: 11.5em;
  font-size: 1.4px;
}

.tr-card-balance-modal.modal {
  width: min(420px, calc(100vw - 32px)) !important;
}

@media (max-width: 980px) {
  .tr-card-balance {
    margin-left: 0;
  }
}
</style>
