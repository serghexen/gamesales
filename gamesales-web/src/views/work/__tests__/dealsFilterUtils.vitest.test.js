import { describe, it, expect } from 'vitest'

import {
  parseMultiValueFilterQuery,
  stringifyMultiValueFilterQuery,
  parseResponsibleFilterQuery,
  stringifyResponsibleFilterQuery,
} from '../dealsFilterUtils.js'

describe('dealsFilterUtils', () => {
  it('parseMultiValueFilterQuery splits and trims values', () => {
    expect(parseMultiValueFilterQuery(' sale , draft,  ,pending ')).toEqual(['sale', 'draft', 'pending'])
    expect(parseMultiValueFilterQuery('')).toEqual([])
  })

  it('stringifyMultiValueFilterQuery joins unique normalized values', () => {
    expect(stringifyMultiValueFilterQuery([' sale ', 'draft', 'sale', '', null])).toBe('sale,draft')
    expect(stringifyMultiValueFilterQuery([])).toBe('')
  })

  it('parseResponsibleFilterQuery splits and trims values', () => {
    expect(parseResponsibleFilterQuery(' Иван , Петр,  ,Ольга ')).toEqual(['Иван', 'Петр', 'Ольга'])
    expect(parseResponsibleFilterQuery('')).toEqual([])
  })

  it('stringifyResponsibleFilterQuery joins unique normalized values', () => {
    expect(stringifyResponsibleFilterQuery([' Иван ', 'Петр', 'Иван', '', null])).toBe('Иван,Петр')
    expect(stringifyResponsibleFilterQuery([])).toBe('')
  })
})
