<template>
  <section class="panel panel--wide">
    <WorkGamesHeader
      :game-filters="ctx.gameFilters"
      :apply-game-search="ctx.applyGameSearch"
      :open-create-game-modal="ctx.openCreateGameModal"
      :open-game-import="ctx.openGameImport"
      :load-games="ctx.loadGames"
      :games-loading="ctx.gamesLoading"
    />
    <div class="panel__body">
      <div v-if="ctx.gamesLoading" class="loader-wrap loader-overlay">
        <div aria-label="Orange and tan hamster running in a metal wheel" role="img" class="wheel-and-hamster">
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
      </div>
      <WorkGameFilterChips
        v-else-if="ctx.activeGameChips.length"
        :active-game-chips="ctx.activeGameChips"
        :reset-game-filter="ctx.resetGameFilter"
      />
      <WorkGameImportModal
        :show-game-import="ctx.showGameImport"
        :close-game-import="ctx.closeGameImport"
        :modal-ref="ctx.modalRef"
        :modal-style="ctx.modalStyle"
        :start-modal-drag="ctx.startModalDrag"
        :game-import-loading="ctx.gameImportLoading"
        :download-game-template="ctx.downloadGameTemplate"
        :validate-game-import="ctx.validateGameImport"
        :game-import-file="ctx.gameImportFile"
        :game-import-action="ctx.gameImportAction"
        :upload-game-import="ctx.uploadGameImport"
        :game-import-validated="ctx.gameImportValidated"
        :game-import-job-id="ctx.gameImportJobId"
        :cancel-game-import="ctx.cancelGameImport"
        :scroll-to-import-details="ctx.scrollToImportDetails"
        :game-import-progress="ctx.gameImportProgress"
        :on-game-import-file="ctx.onGameImportFile"
        :import-details-ref="ctx.importDetailsRef"
        :game-import-message="ctx.gameImportMessage"
        :game-import-errors="ctx.gameImportErrors"
        :game-import-warnings="ctx.gameImportWarnings"
        :download-game-import-report="ctx.downloadGameImportReport"
        :game-import-stats="ctx.gameImportStats"
      />

      <WorkGamesTableSection
        :sorted-games="ctx.sortedGames"
        :paged-games="ctx.pagedGames"
        :game-filters="ctx.gameFilters"
        :active-game-filter="ctx.activeGameFilter"
        :game-filter-draft="ctx.gameFilterDraft"
        :open-game-filter="ctx.openGameFilter"
        :toggle-games-sort="ctx.toggleGamesSort"
        :get-games-sort-class="ctx.getGamesSortClass"
        :apply-game-filter="ctx.applyGameFilter"
        :reset-game-filter="ctx.resetGameFilter"
        :format-game-platforms="ctx.formatGamePlatforms"
        :open-game-accounts="ctx.openGameAccounts"
      />

      <WorkGamesPager
        :games-total="ctx.gamesTotal"
        :games-page-size="ctx.gamesPageSize"
        :set-games-page-size="ctx.setGamesPageSizeFromEvent"
        :games-page="ctx.gamesPage"
        :set-games-page="ctx.setGamesPage"
        :prev-games-page="ctx.prevGamesPage"
        :games-page-input="ctx.gamesPageInput"
        :set-games-page-input="ctx.setGamesPageInputFromEvent"
        :games-total-pages="ctx.gamesTotalPages"
        :jump-games-page="ctx.jumpGamesPage"
        :next-games-page="ctx.nextGamesPage"
      />

      <div class="divider"></div>

      <WorkGameEditorModal :ctx="ctx.gameEditorModalCtx" />
    </div>
  </section>
</template>

<script setup>
import WorkGamesHeader from './WorkGamesHeader.vue'
import WorkGameFilterChips from './WorkGameFilterChips.vue'
import WorkGameImportModal from './WorkGameImportModal.vue'
import WorkGamesTableSection from './WorkGamesTableSection.vue'
import WorkGamesPager from './WorkGamesPager.vue'
import WorkGameEditorModal from './WorkGameEditorModal.vue'

// Контекст секции игр: фильтры, таблица, пагинация, импорт и модалка.
defineProps({
  ctx: {
    type: Object,
    required: true,
  },
})
</script>
