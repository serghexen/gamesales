import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('WorkView RBAC fallbacks', () => {
  it('uses backend-compatible action defaults instead of allowing missing actions', () => {
    const filePath = resolve(process.cwd(), 'src/views/WorkView.vue')
    const source = readFileSync(filePath, 'utf8')

    expect(source).toContain("const defaultFalseActions = new Set([")
    expect(source).toContain("'deals_active.discount'")
    expect(source).toContain('function defaultActionAllowedByRole(actionCode, roleCode) {')
    expect(source).toContain('return defaultActionAllowedByRole(code, auth.state.role)')
    expect(source).not.toContain('if (Object.prototype.hasOwnProperty.call(map, code)) return Boolean(map[code])\n  return true')
  })
})
