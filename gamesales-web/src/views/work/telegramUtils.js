export function createTelegramState() {
  return {
    status: 'not_connected',
    phone: '',
    code: '',
    password: '',
    loadingMessages: false,
    loadingOlderMessages: false,
    hasMoreOlderMessages: true,
    autoStickBottom: true,
    dialogStatusFilter: 'new',
    dialogCounts: { new: 0, accepted: 0, archived: 0, all: 0 },
    dialogsSyncRunning: false,
    dialogsLastSyncAt: '',
    dialogsSyncLoaded: 0,
    dialogsSyncBatches: 0,
    dialogs: [],
    activeChatId: null,
    activeDialog: null,
    messages: [],
    messageText: '',
    activeContactId: null,
    contact: {
      title: '',
      info: '',
    },
    contactMeta: {
      name: '',
      username: '',
    },
    contactEdit: {
      title: '',
      info: '',
    },
    contactEditing: false,
    loading: false,
    error: '',
    info: '',
  }
}

export function formatTelegramSender(message) {
  if (!message) return ''
  if (message.sender_name) return message.sender_name
  if (message.sender_username) return `@${message.sender_username}`
  return ''
}

export function formatTelegramMessageHtml(value) {
  const src = value == null ? '' : String(value)
  const escaped = src
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')

  const withLinks = escaped.replace(
    /(https?:\/\/[^\s<]+)/gi,
    '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>'
  )
  return withLinks.replace(/\r?\n/g, '<br>')
}

export function showTelegramChannelLabel(messages, index) {
  const list = Array.isArray(messages) ? messages : []
  const current = list[index]
  if (!current || current.out) return false
  const next = list[index + 1]
  if (!next) return true
  if (next.out) return true
  if ((next.sender_id || null) !== (current.sender_id || null)) return true
  return false
}

export function isTelegramImage(message) {
  // Проверка: можно ли показать сообщение как картинку.
  if (!message?.media_url) return false
  if (message?.media_type === 'photo' || message?.media_type === 'gif') return true
  const mime = message?.mime_type || ''
  return mime.startsWith('image/')
}

export function isTelegramVideo(message) {
  // Проверка: можно ли показать сообщение как видео.
  if (!message?.media_url) return false
  if (message?.media_type === 'video') return true
  const mime = message?.mime_type || ''
  return mime.startsWith('video/')
}
