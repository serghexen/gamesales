<template>
  <section class="panel panel--wide">
    <div class="panel__head">
      <div>
        <div class="toolbar-actions">
          <button
            class="btn btn--icon btn--glow btn--glow-refresh"
            type="button"
            @click="ctx.loadTelegramStatus"
            :disabled="ctx.telegram.loading || (ctx.telegram.status === 'ready' && ctx.telegram.dialogsSyncRunning)"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M20 12a8 8 0 1 1-2.3-5.7" />
              <path d="M20 4v6h-6" />
            </svg>
          </button>
          <button
            v-if="ctx.isAdmin && ctx.telegram.status === 'ready'"
            class="btn btn--icon btn--glow btn--glow-close"
            type="button"
            @click="ctx.tgAuthDisconnect"
            :disabled="ctx.telegram.loading"
            title="Отвязать Telegram"
            aria-label="Отвязать Telegram"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M6 6l12 12M18 6l-12 12" />
            </svg>
          </button>
        </div>
      </div>
    </div>
    <div class="panel__body">
      <div v-if="ctx.telegram.error" class="bad">{{ ctx.telegram.error }}</div>
      <div v-if="ctx.telegram.info" class="ok">{{ ctx.telegram.info }}</div>

      <div v-if="ctx.telegram.status !== 'ready'" class="tg-auth">
        <div v-if="ctx.isAdmin" class="tg-auth__card">
          <h3>Подключение Telegram</h3>
          <label class="field">
            <span class="label">Телефон</span>
            <input v-model.trim="ctx.telegram.phone" class="input" placeholder="+79990001122" />
          </label>
          <button class="btn btn--icon btn--glow btn--glow-add" type="button" @click="ctx.tgAuthStart" :disabled="ctx.telegram.loading">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M12 5v14M5 12h14" />
            </svg>
          </button>
        </div>
        <div v-if="ctx.isAdmin" class="tg-auth__card">
          <h3>Код подтверждения</h3>
          <label class="field">
            <span class="label">Код</span>
            <input v-model.trim="ctx.telegram.code" class="input" placeholder="12345" />
          </label>
          <button class="btn btn--icon btn--glow btn--glow-add" type="button" @click="ctx.tgAuthConfirm" :disabled="ctx.telegram.loading">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M5 13l4 4L19 7" />
            </svg>
          </button>
        </div>
        <div v-if="ctx.isAdmin && ctx.telegram.status === 'password_required'" class="tg-auth__card">
          <h3>Пароль 2FA</h3>
          <label class="field">
            <span class="label">Пароль</span>
            <input v-model.trim="ctx.telegram.password" class="input" type="password" />
          </label>
          <button class="btn btn--icon btn--glow btn--glow-add" type="button" @click="ctx.tgAuthPassword" :disabled="ctx.telegram.loading">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M5 13l4 4L19 7" />
            </svg>
          </button>
        </div>
        <div v-if="!ctx.isAdmin" class="tg-auth__card">
          <h3>Telegram не подключен</h3>
          <p class="muted">Подключение выполняет администратор.</p>
        </div>
      </div>

      <div v-else class="tg-shell">
        <div class="tg-dialogs">
          <div class="tg-dialogs__head">
            <div class="tg-dialog-tabs" role="tablist" aria-label="Статусы диалогов">
              <button
                class="tg-dialog-tab"
                :class="{ active: ctx.telegram.dialogStatusFilter === 'new' }"
                type="button"
                @click="ctx.setTelegramDialogFilter('new')"
              >
                Новые
                <span v-if="ctx.telegram.dialogCounts.new" class="tg-dialog-tab__count">{{ ctx.telegram.dialogCounts.new }}</span>
              </button>
              <button
                class="tg-dialog-tab"
                :class="{ active: ctx.telegram.dialogStatusFilter === 'accepted' }"
                type="button"
                @click="ctx.setTelegramDialogFilter('accepted')"
              >
                Принятые
                <span v-if="ctx.telegram.dialogCounts.accepted" class="tg-dialog-tab__count">{{ ctx.telegram.dialogCounts.accepted }}</span>
              </button>
              <button
                class="tg-dialog-tab"
                :class="{ active: ctx.telegram.dialogStatusFilter === 'archived' }"
                type="button"
                @click="ctx.setTelegramDialogFilter('archived')"
              >
                Архив
                <span v-if="ctx.telegram.dialogCounts.archived" class="tg-dialog-tab__count">{{ ctx.telegram.dialogCounts.archived }}</span>
              </button>
            </div>
            <div class="tg-dialogs__meta">
              <span v-if="ctx.telegram.dialogsSyncRunning" class="tg-dialogs__meta-pill tg-dialogs__meta-pill--running">
                Синхро: идет • батч {{ ctx.telegram.dialogsSyncBatches || 0 }} • загружено {{ ctx.telegram.dialogsSyncLoaded || 0 }}
              </span>
              <span v-else-if="ctx.telegram.dialogsLastSyncAt" class="tg-dialogs__meta-pill">Синхро: {{ ctx.formatDateTimeMinutes(ctx.telegram.dialogsLastSyncAt) }}</span>
              <span v-else class="tg-dialogs__meta-pill">Синхро: нет</span>
              <span class="tg-dialogs__meta-pill tg-dialogs__meta-pill--count">Контактов: {{ ctx.telegram.dialogCounts.all || 0 }}</span>
            </div>
          </div>
          <div class="tg-dialogs__list">
            <button
              v-for="d in ctx.telegram.dialogs"
              :key="d.id"
              class="tg-dialog"
              :class="{ active: ctx.telegram.activeChatId === d.id }"
              type="button"
              @click="ctx.selectTelegramDialog(d.id)"
            >
              <span class="tg-dialog__title">{{ d.title || d.id }}</span>
              <span class="tg-dialog__unread" :class="{ 'tg-dialog__unread--zero': !d.unread_count }">{{ d.unread_count || 0 }}</span>
            </button>
            <p v-if="!ctx.telegram.dialogs.length" class="muted">Чаты не найдены.</p>
          </div>
        </div>
        <div class="tg-messages">
          <div v-if="ctx.telegram.loadingMessages" class="tg-loading-overlay">
            <div class="loader-wrap loader-wrap--compact">
              <div class="newtons-cradle" aria-label="Loading" role="img">
                <div class="newtons-cradle__dot"></div>
                <div class="newtons-cradle__dot"></div>
                <div class="newtons-cradle__dot"></div>
                <div class="newtons-cradle__dot"></div>
              </div>
              <p class="muted">Загрузка сообщений...</p>
            </div>
          </div>
          <div class="tg-contact">
            <div class="tg-contact__head">
              <div class="tg-contact__title">{{ ctx.telegram.contact.title || ctx.telegram.contactMeta.name || ctx.telegram.contactMeta.username || 'Контакт' }}</div>
              <div class="tg-contact__tools">
                <button
                  v-if="ctx.telegram.activeDialog && ctx.telegram.activeDialog.status !== 'accepted'"
                  class="ghost ghost--tiny"
                  type="button"
                  @click="ctx.setTelegramDialogStatus('accepted')"
                  :disabled="ctx.telegram.loading || !ctx.telegram.activeChatId"
                >
                  Принять
                </button>
                <button
                  v-if="ctx.telegram.activeDialog && ctx.telegram.activeDialog.status !== 'archived'"
                  class="ghost ghost--tiny"
                  type="button"
                  @click="ctx.setTelegramDialogStatus('archived')"
                  :disabled="ctx.telegram.loading || !ctx.telegram.activeChatId"
                >
                  В архив
                </button>
                <button
                  v-if="ctx.telegram.activeDialog && ctx.telegram.activeDialog.status === 'archived'"
                  class="ghost ghost--tiny"
                  type="button"
                  @click="ctx.setTelegramDialogStatus('accepted')"
                  :disabled="ctx.telegram.loading || !ctx.telegram.activeChatId"
                >
                  Из архива
                </button>
                <button class="btn btn--icon btn--glow btn--glow-edit" type="button" @click="ctx.toggleTelegramContactEdit" :disabled="!ctx.telegram.activeContactId">
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M4 20h4l10-10-4-4L4 16v4z" />
                    <path d="M14 6l4 4" />
                  </svg>
                </button>
              </div>
            </div>
            <div class="tg-contact__info">
              {{
                ctx.telegram.contact.info ||
                (ctx.telegram.contactMeta.username ? `@${ctx.telegram.contactMeta.username}` : '') ||
                (ctx.telegram.activeContactId ? `ID: ${ctx.telegram.activeContactId}` : '—')
              }}
            </div>
            <div v-if="ctx.telegram.contactEditing" class="tg-contact__edit">
              <input v-model.trim="ctx.telegram.contactEdit.title" class="input" placeholder="Заголовок" />
              <input v-model.trim="ctx.telegram.contactEdit.info" class="input" placeholder="Информация" />
              <div class="tg-contact__actions">
                <button class="btn btn--icon btn--glow btn--glow-save" type="button" @click="ctx.saveTelegramContact" :disabled="ctx.telegram.loading">
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M4 4h12l4 4v12H4z" />
                    <path d="M7 4v6h8V4" />
                    <path d="M7 20v-6h10v6" />
                  </svg>
                </button>
                <button class="btn btn--icon btn--glow btn--glow-close" type="button" @click="ctx.cancelTelegramContactEdit">
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M6 6l12 12M18 6l-12 12" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
          <TransitionGroup
            :ref="ctx.tgMessagesList"
            tag="div"
            name="tg-message-fade"
            class="tg-messages__list"
            @scroll="ctx.onTelegramMessagesScroll"
          >
            <div v-if="ctx.telegram.loadingOlderMessages" key="__loading_older__" class="tg-messages__older-loading">
              Загрузка старых сообщений...
            </div>
            <div
              v-for="(m, idx) in ctx.telegram.messages"
              :key="m.id"
              class="tg-message-row"
              :class="{ 'tg-message-row--out': m.out }"
            >
              <div
                class="tg-message"
                :class="{ 'tg-message--out': m.out, 'tg-message--active': m.sender_id && m.sender_id === ctx.telegram.activeContactId }"
                @click="ctx.setTelegramActiveContact(m.sender_id)"
              >
                <div class="tg-message__text" v-html="ctx.formatTelegramMessageHtml(m.text || '—')"></div>
                <div v-if="ctx.telegram.activeDialog?.is_group && !m.out && ctx.formatTelegramSender(m)" class="tg-message__sender">
                  {{ ctx.formatTelegramSender(m) }}
                </div>
                <div v-if="m.has_media" class="tg-message__media">
                  <img
                    v-if="ctx.isTelegramImage(m) && m.media_url"
                    :src="m.media_url"
                    :alt="m.media_type === 'gif' ? 'GIF' : 'Image'"
                    @load="ctx.onTelegramMediaRendered"
                  />
                  <video v-else-if="ctx.isTelegramVideo(m) && m.media_url" :src="m.media_url" controls @loadedmetadata="ctx.onTelegramMediaRendered" />
                  <a v-else-if="m.media_url" :href="m.media_url" target="_blank" rel="noopener">
                    Открыть файл
                  </a>
                  <div v-else class="tg-message__media-placeholder" aria-label="Загрузка медиа">
                    <span class="muted">Загрузка...</span>
                  </div>
                </div>
                <div class="tg-message__meta">
                  <span v-if="m.sent_by" class="tg-message__sent-by">Отправил: {{ m.sent_by }}</span>
                  <span>{{ ctx.formatDateTimeMinutes(m.date) }}</span>
                </div>
                <div v-if="ctx.showTelegramChannelLabel(idx)" class="tg-message__channel">
                  Получено из Telegram {{ ctx.telegram.activeDialog?.is_group ? 'Группа' : 'Личный' }} — ASAT
                </div>
              </div>
              <div v-if="!m.out" class="tg-message-row__actions">
                <button class="tg-message-action tg-message-action--blue" type="button" title="Ответить" @click.stop>
                  <span class="tg-message-action__glyph" aria-hidden="true">↩</span>
                </button>
                <button class="tg-message-action tg-message-action--red" type="button" title="Перенаправить" @click.stop>
                  <span class="tg-message-action__glyph" aria-hidden="true">↪</span>
                </button>
              </div>
              <div v-if="m.out" class="tg-message-row__actions-spacer" aria-hidden="true">
                <div class="tg-message-action tg-message-action--ghost"></div>
                <div class="tg-message-action tg-message-action--ghost"></div>
              </div>
            </div>
          </TransitionGroup>
          <div class="tg-compose">
            <div class="tg-compose__head">
              <span class="tg-compose__brand">ASAT</span>
              <span class="tg-compose__title">ответ в</span>
              <button class="tg-compose__link" type="button">сообщение</button>
            </div>
            <div class="tg-compose__body">
              <textarea
                v-model.trim="ctx.telegram.messageText"
                class="tg-compose__input"
                placeholder="Введите сообщение..."
              />
              <div class="tg-compose__actions">
                <button class="tg-compose__icon" type="button" aria-label="Голос" title="Голос">
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M12 4a3 3 0 0 1 3 3v5a3 3 0 0 1-6 0V7a3 3 0 0 1 3-3z" />
                    <path d="M19 11a7 7 0 0 1-14 0" />
                    <path d="M12 18v3" />
                  </svg>
                </button>
                <button class="tg-compose__icon" type="button" aria-label="Просмотр" title="Просмотр">
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                </button>
                <button class="tg-compose__icon" type="button" aria-label="Вложение" title="Вложение">
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M21 12.5V17a2 2 0 0 1-2 2h-4.5" />
                    <path d="M3 11.5V7a2 2 0 0 1 2-2h4.5" />
                    <path d="M14 5h5v5" />
                    <path d="M10 19H5v-5" />
                    <path d="M19 5l-8 8" />
                    <path d="M5 19l8-8" />
                  </svg>
                </button>
                <button class="tg-compose__icon" type="button" aria-label="Скрепка" title="Скрепка">
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M21.44 11.05l-8.49 8.49a6 6 0 0 1-8.49-8.49l8.49-8.49a4 4 0 0 1 5.66 5.66L10.6 16.24a2 2 0 0 1-2.83-2.83l7.07-7.07" />
                  </svg>
                </button>
                <button class="tg-compose__icon" type="button" aria-label="Emoji" title="Emoji">
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <circle cx="12" cy="12" r="9" />
                    <path d="M9 10h.01M15 10h.01" />
                    <path d="M8 14c1 1.5 2.5 2 4 2s3-.5 4-2" />
                  </svg>
                </button>
                <button
                  class="tg-compose__send"
                  type="button"
                  @click="ctx.sendTelegramMessage"
                  :disabled="ctx.telegram.loading || !ctx.telegram.activeChatId || !ctx.telegram.messageText"
                  aria-label="Отправить"
                  title="Отправить"
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M3 20l18-8L3 4v6l12 2-12 2z" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
// Контекст содержит состояние и действия Telegram-вкладки из WorkView.
defineProps({
  ctx: {
    type: Object,
    required: true,
  },
})
</script>
