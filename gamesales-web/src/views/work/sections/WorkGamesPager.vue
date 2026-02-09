<template>
  <div v-if="gamesTotal > 0" class="pager">
    <span class="muted">Всего: {{ gamesTotal }}</span>
    <label class="pager__size">
      <span class="label">Показывать</span>
      <select :value="gamesPageSize" class="input input--select input--compact" @change="setGamesPageSize($event)">
        <option :value="20">20</option>
        <option :value="50">50</option>
        <option :value="100">100</option>
      </select>
    </label>
    <button class="ghost" @click="setGamesPage(1)" :disabled="gamesPage <= 1">
      «
    </button>
    <button class="ghost" @click="prevGamesPage" :disabled="gamesPage <= 1">
      ← Назад
    </button>
    <label class="pager__jump">
      <span class="muted">Стр.</span>
      <input
        :value="gamesPageInput"
        class="input input--compact input--page"
        type="number"
        min="1"
        :max="gamesTotalPages"
        @input="setGamesPageInput($event)"
        @keydown.enter.prevent="jumpGamesPage"
        @blur="jumpGamesPage"
      />
    </label>
    <span class="muted">из {{ gamesTotalPages }}</span>
    <button class="ghost" @click="nextGamesPage" :disabled="gamesPage >= gamesTotalPages">
      Вперёд →
    </button>
    <button class="ghost" @click="setGamesPage(gamesTotalPages)" :disabled="gamesPage >= gamesTotalPages">
      »
    </button>
  </div>
</template>

<script setup>
defineProps({
  gamesTotal: { type: Number, required: true },
  gamesPageSize: { type: Number, required: true },
  setGamesPageSize: { type: Function, required: true },
  gamesPage: { type: Number, required: true },
  setGamesPage: { type: Function, required: true },
  prevGamesPage: { type: Function, required: true },
  gamesPageInput: { type: Number, required: true },
  setGamesPageInput: { type: Function, required: true },
  gamesTotalPages: { type: Number, required: true },
  jumpGamesPage: { type: Function, required: true },
  nextGamesPage: { type: Function, required: true },
})
</script>
