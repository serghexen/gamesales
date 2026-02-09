<template>
  <table v-if="sortedGames.length" class="table table--compact">
    <thead>
      <tr>
        <th>
          <span class="th-title th-title--filter">
            Игра
            <span class="th-actions">
              <button
                class="filter-icon"
                :class="{ 'filter-icon--active': Boolean(gameFilters.q) }"
                type="button"
                aria-label="Фильтр по игре"
                title="Фильтр по игре"
                @click.stop="openGameFilter('title')"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 6h16M7 12h10M10 18h4" />
                </svg>
              </button>
              <button
                class="filter-icon filter-icon--sort"
                type="button"
                aria-label="Сортировка по игре"
                title="Сортировка по игре"
                @click.stop="toggleGamesSort('title')"
                :class="getGamesSortClass('title')"
              >
                <svg viewBox="0 0 24 24">
                  <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                  <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                </svg>
              </button>
            </span>
          </span>
          <div v-if="activeGameFilter === 'title'" class="filter-pop filter-pop--center" @click.stop>
            <label class="field">
              <span class="label">Игра</span>
              <input v-model.trim="gameFilterDraft.title" class="input" placeholder="игра" />
            </label>
            <button class="ghost ghost--small" type="button" @click="applyGameFilter('title')">Применить</button>
            <button class="ghost ghost--small" type="button" @click="resetGameFilter('title')">Сбросить</button>
          </div>
        </th>
        <th>Короткое</th>
        <th>
          <span class="th-title th-title--filter">
            Платформа
            <span class="th-actions">
              <button
                class="filter-icon"
                :class="{ 'filter-icon--active': Boolean(gameFilters.platform_code) }"
                type="button"
                aria-label="Фильтр по платформе"
                title="Фильтр по платформе"
                @click.stop="openGameFilter('platform')"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 6h16M7 12h10M10 18h4" />
                </svg>
              </button>
              <button
                class="filter-icon filter-icon--sort"
                type="button"
                aria-label="Сортировка по платформе"
                title="Сортировка по платформе"
                @click.stop="toggleGamesSort('platform')"
                :class="getGamesSortClass('platform')"
              >
                <svg viewBox="0 0 24 24">
                  <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                  <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                </svg>
              </button>
            </span>
          </span>
          <div v-if="activeGameFilter === 'platform'" class="filter-pop filter-pop--center" @click.stop>
            <label class="field">
              <span class="label">Платформа</span>
              <input v-model.trim="gameFilterDraft.platform" class="input" placeholder="платформа" />
            </label>
            <button class="ghost ghost--small" type="button" @click="applyGameFilter('platform')">Применить</button>
            <button class="ghost ghost--small" type="button" @click="resetGameFilter('platform')">Сбросить</button>
          </div>
        </th>
        <th>
          <span class="th-title th-title--filter">
            Регион
            <span class="th-actions">
              <button
                class="filter-icon"
                :class="{ 'filter-icon--active': Boolean(gameFilters.region_code) }"
                type="button"
                aria-label="Фильтр по региону"
                title="Фильтр по региону"
                @click.stop="openGameFilter('region')"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 6h16M7 12h10M10 18h4" />
                </svg>
              </button>
              <button
                class="filter-icon filter-icon--sort"
                type="button"
                aria-label="Сортировка по региону"
                title="Сортировка по региону"
                @click.stop="toggleGamesSort('region')"
                :class="getGamesSortClass('region')"
              >
                <svg viewBox="0 0 24 24">
                  <path class="sort-icon__up" d="M7 10l5-5 5 5" />
                  <path class="sort-icon__down" d="M7 14l5 5 5-5" />
                </svg>
              </button>
            </span>
          </span>
          <div v-if="activeGameFilter === 'region'" class="filter-pop filter-pop--right" @click.stop>
            <label class="field">
              <span class="label">Регион</span>
              <input v-model.trim="gameFilterDraft.region" class="input" placeholder="регион" />
            </label>
            <button class="ghost ghost--small" type="button" @click="applyGameFilter('region')">Применить</button>
            <button class="ghost ghost--small" type="button" @click="resetGameFilter('region')">Сбросить</button>
          </div>
        </th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="g in pagedGames" :key="g.game_id" class="clickable-row" @click="openGameAccounts(g)">
        <td>{{ g.title }}</td>
        <td>{{ g.short_title || '—' }}</td>
        <td>{{ formatGamePlatforms(g.platform_codes) }}</td>
        <td>{{ g.region_code || '—' }}</td>
      </tr>
    </tbody>
  </table>
  <p v-else class="muted">Пока нет игр.</p>
</template>

<script setup>
defineProps({
  sortedGames: { type: Array, required: true },
  pagedGames: { type: Array, required: true },
  gameFilters: { type: Object, required: true },
  activeGameFilter: { type: String, default: '' },
  gameFilterDraft: { type: Object, required: true },
  openGameFilter: { type: Function, required: true },
  toggleGamesSort: { type: Function, required: true },
  getGamesSortClass: { type: Function, required: true },
  applyGameFilter: { type: Function, required: true },
  resetGameFilter: { type: Function, required: true },
  formatGamePlatforms: { type: Function, required: true },
  openGameAccounts: { type: Function, required: true },
})
</script>
