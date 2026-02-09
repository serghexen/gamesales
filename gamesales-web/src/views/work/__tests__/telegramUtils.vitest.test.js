import { describe, it, expect } from 'vitest'

import {
  createTelegramState,
  formatTelegramSender,
  formatTelegramMessageHtml,
  showTelegramChannelLabel,
  isTelegramImage,
  isTelegramVideo,
} from '../telegramUtils.js'

describe('telegramUtils', () => {
  it('createTelegramState returns expected defaults', () => {
    const state = createTelegramState()
    expect(state.status).toBe('not_connected')
    expect(state.loading).toBe(false)
    expect(state.dialogStatusFilter).toBe('new')
    expect(state.dialogCounts).toEqual({ new: 0, accepted: 0, archived: 0, all: 0 })
  })

  it('formatTelegramSender prefers name, then username', () => {
    expect(formatTelegramSender({ sender_name: 'Ivan', sender_username: 'ivan' })).toBe('Ivan')
    expect(formatTelegramSender({ sender_name: '', sender_username: 'ivan' })).toBe('@ivan')
    expect(formatTelegramSender({})).toBe('')
    expect(formatTelegramSender(null)).toBe('')
  })

  it('formatTelegramMessageHtml escapes html, keeps links and line breaks', () => {
    const text = '<b>Hello</b>\nhttps://example.com?q=1&x=2'
    const html = formatTelegramMessageHtml(text)
    expect(html).toContain('&lt;b&gt;Hello&lt;/b&gt;')
    expect(html).toContain('<br>')
    expect(html).toContain('<a href="https://example.com?q=1&amp;x=2"')
  })

  it('showTelegramChannelLabel respects sender and direction', () => {
    const messages = [
      { sender_id: 1, out: false },
      { sender_id: 1, out: false },
      { sender_id: 2, out: false },
      { sender_id: 2, out: true },
    ]

    expect(showTelegramChannelLabel(messages, 0)).toBe(false)
    expect(showTelegramChannelLabel(messages, 1)).toBe(true)
    expect(showTelegramChannelLabel(messages, 2)).toBe(true)
    expect(showTelegramChannelLabel(messages, 3)).toBe(false)
    expect(showTelegramChannelLabel([], 0)).toBe(false)
  })

  it('isTelegramImage detects image media by type or mime', () => {
    expect(isTelegramImage({ media_url: 'x', media_type: 'photo' })).toBe(true)
    expect(isTelegramImage({ media_url: 'x', media_type: 'gif' })).toBe(true)
    expect(isTelegramImage({ media_url: 'x', mime_type: 'image/png' })).toBe(true)
    expect(isTelegramImage({ media_url: 'x', media_type: 'video', mime_type: 'video/mp4' })).toBe(false)
    expect(isTelegramImage({ media_type: 'photo' })).toBe(false)
  })

  it('isTelegramVideo detects video media by type or mime', () => {
    expect(isTelegramVideo({ media_url: 'x', media_type: 'video' })).toBe(true)
    expect(isTelegramVideo({ media_url: 'x', mime_type: 'video/mp4' })).toBe(true)
    expect(isTelegramVideo({ media_url: 'x', media_type: 'photo', mime_type: 'image/png' })).toBe(false)
    expect(isTelegramVideo({ media_type: 'video' })).toBe(false)
  })
})
