<template>
  <table v-if="sortedAccounts.length" class="table table--compact">
    <thead>
      <tr>
        <th class="cell--account">
          <span class="th-title th-title--filter">
            Почта
            <span class="th-actions">
              <button
                class="filter-icon"
                :class="{ 'filter-icon--active': Boolean(accountFilters.login_q) }"
                type="button"
                aria-label="Фильтр по почте"
                title="Фильтр по почте"
                @click.stop="openAccountFilter('login')"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 6h16M7 12h10M10 18h4" />
                </svg>
              </button>
              <button
                class="filter-icon filter-icon--sort"
                type="button"
                aria-label="Сортировка по почте"
                title="Сортировка по почте"
                @click.stop="toggleAccountSort('login')"
                :class="getAccountSortClass('login')"
              >
                <svg viewBox="0 0 24 24">
                  <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                  <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                </svg>
              </button>
            </span>
          </span>
          <div v-if="activeAccountFilter === 'login'" class="filter-pop filter-pop--left" @click.stop>
            <label class="field">
              <span class="label">Почта</span>
              <input v-model.trim="accountFilterDraft.login" class="input" placeholder="почта" />
            </label>
            <button class="ghost ghost--small" type="button" @click="applyAccountFilter('login')">Применить</button>
            <button class="ghost ghost--small" type="button" @click="resetAccountFilter('login')">Сбросить</button>
          </div>
        </th>
        <th>
          <span class="th-title th-title--filter">
            Товары
            <span class="th-actions">
              <button
                class="filter-icon"
                :class="{ 'filter-icon--active': Boolean(accountFilters.product_q) }"
                type="button"
                aria-label="Фильтр по товарам"
                title="Фильтр по товарам"
                @click.stop="openAccountFilter('product')"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 6h16M7 12h10M10 18h4" />
                </svg>
              </button>
              <button
                class="filter-icon filter-icon--sort"
                type="button"
                aria-label="Сортировка по товарам"
                title="Сортировка по товарам"
                @click.stop="toggleAccountSort('products')"
                :class="getAccountSortClass('products')"
              >
                <svg viewBox="0 0 24 24">
                  <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                  <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                </svg>
              </button>
            </span>
          </span>
          <div v-if="activeAccountFilter === 'product'" class="filter-pop filter-pop--center" @click.stop>
            <label class="field">
              <span class="label">Товар</span>
              <input v-model.trim="accountFilterDraft.product" class="input" placeholder="название товара" />
            </label>
            <button class="ghost ghost--small" type="button" @click="applyAccountFilter('product')">Применить</button>
            <button class="ghost ghost--small" type="button" @click="resetAccountFilter('product')">Сбросить</button>
          </div>
        </th>
        <th>Слоты</th>
        <th>Резерв</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="a in sortedAccounts" :key="a.account_id" class="clickable-row" @click="startEditAccount(a)">
        <td class="cell--account">{{ a.login_full || '—' }}</td>
        <td>{{ formatAccountProductsLine(a) }}</td>
        <td class="cell--slots">
          <span v-if="!getAccountSlotStatusList(a).length" class="slot-line">—</span>
          <span v-for="s in getAccountSlotStatusList(a)" :key="s.slot_type_code" class="slot-line">
            {{ formatAccountSlotStatusLine(s) }}
          </span>
        </td>
        <td class="cell--selectable" @click.stop>{{ formatSecret(getReserveSecrets(a.account_id)) }}</td>
      </tr>
    </tbody>
  </table>
  <p v-else class="muted">Пока нет аккаунтов.</p>
</template>

<script setup>
defineProps({
  sortedAccounts: { type: Array, required: true },
  accountFilters: { type: Object, required: true },
  activeAccountFilter: { type: String, default: '' },
  accountFilterDraft: { type: Object, required: true },
  openAccountFilter: { type: Function, required: true },
  toggleAccountSort: { type: Function, required: true },
  getAccountSortClass: { type: Function, required: true },
  applyAccountFilter: { type: Function, required: true },
  resetAccountFilter: { type: Function, required: true },
  startEditAccount: { type: Function, required: true },
  formatAccountProductsLine: { type: Function, required: true },
  getAccountSlotStatusList: { type: Function, required: true },
  formatAccountSlotStatusLine: { type: Function, required: true },
  formatSecret: { type: Function, required: true },
  getReserveSecrets: { type: Function, required: true },
})
</script>
