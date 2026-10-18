import { describe, expect, it } from 'vitest'
import {
  appliedDateLabel,
  formatLegalDate,
  isInForceOn,
  todayIso,
  toLegalAnswerInfo,
  validityLabel,
} from './format'

describe('legal date formatting', () => {
  it('formats ISO dates without building a Date (no timezone shift)', () => {
    expect(formatLegalDate('2026-07-01')).toBe('01/07/2026')
    expect(formatLegalDate('2026-07-01T00:00:00')).toBe('01/07/2026')
    expect(formatLegalDate('')).toBe('')
    expect(formatLegalDate(null)).toBe('')
    expect(formatLegalDate('không phải ngày')).toBe('không phải ngày')
  })

  it('labels validity intervals', () => {
    expect(validityLabel('2024-08-01', null)).toBe('Hiệu lực 01/08/2024 → nay')
    expect(validityLabel('2024-08-01', '2026-07-01')).toBe('Hiệu lực 01/08/2024 → 01/07/2026')
  })

  it('checks validity with an exclusive end date', () => {
    expect(isInForceOn('2024-08-01', '2026-07-01', '2026-06-30')).toBe(true)
    expect(isInForceOn('2024-08-01', '2026-07-01', '2026-07-01')).toBe(false)
    expect(isInForceOn('2026-07-01', null, '2030-01-01')).toBe(true)
    expect(isInForceOn('2026-07-01', null, '2026-06-30')).toBe(false)
  })

  it('builds today from local date parts', () => {
    expect(todayIso(new Date(2026, 9, 5, 23, 30))).toBe('2026-10-05')
  })
})

describe('legal answer info', () => {
  it('describes single and compare answers', () => {
    expect(appliedDateLabel({ mode: 'single', dates: ['2026-10-15'], notices: [] })).toBe(
      'Áp dụng tại ngày 15/10/2026',
    )
    expect(
      appliedDateLabel({ mode: 'compare', dates: ['2026-06-30', '2026-07-01'], notices: [] }),
    ).toBe('So sánh quy định ngày 30/06/2026 và ngày 01/07/2026')
  })

  it('accepts only well-formed payloads', () => {
    expect(
      toLegalAnswerInfo({ mode: 'single', dates: ['2026-10-15'], temporal_source: 'rule', notices: ['x'] }),
    ).toEqual({ mode: 'single', dates: ['2026-10-15'], temporal_source: 'rule', notices: ['x'] })
    expect(toLegalAnswerInfo({ mode: 'single', dates: ['2026-10-15'] })).toEqual({
      mode: 'single',
      dates: ['2026-10-15'],
      temporal_source: undefined,
      notices: [],
    })
    expect(toLegalAnswerInfo({ mode: 'range', dates: ['2026-10-15'] })).toBeUndefined()
    expect(toLegalAnswerInfo({ mode: 'single', dates: [] })).toBeUndefined()
    expect(toLegalAnswerInfo({ error: 'unavailable' })).toBeUndefined()
    expect(toLegalAnswerInfo(undefined)).toBeUndefined()
  })
})
