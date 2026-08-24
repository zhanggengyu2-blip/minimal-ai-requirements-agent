import { describe, expect, it } from 'vitest'
import {
  addBusinessDays,
  buildGanttRange,
  buildHeaderBands,
  dateAtScrollCenter,
  dateToOrdinal,
  ganttBarGeometry,
  scrollLeftForDate,
} from './gantt'

describe('gantt date calculations', () => {
  it('uses calendar-only arithmetic across leap days and time zones', () => {
    expect(addBusinessDays('2024-02-28', 1)).toBe('2024-02-29')
    expect(addBusinessDays('2024-02-29', 1)).toBe('2024-03-01')
    expect(dateToOrdinal('2026-08-24') - dateToOrdinal('2026-08-23')).toBe(1)
  })

  it('draws inclusive task bars only when both dates are present', () => {
    expect(ganttBarGeometry('2026-08-24', '2026-08-28', '2026-08-20', 30)).toEqual({
      left: 122,
      width: 146,
      durationDays: 5,
    })
    expect(ganttBarGeometry('2026-08-24', null, '2026-08-20', 30)).toBeNull()
  })

  it('builds stable week bands and centers a business date', () => {
    const range = buildGanttRange(['2026-08-18', '2026-09-12'], '2026-08-24')
    const bands = buildHeaderBands(range, 'week')
    expect(bands.primary.length).toBeGreaterThan(1)
    expect(bands.secondary.some((band) => band.label.includes('–'))).toBe(true)
    const left = scrollLeftForDate('2026-08-24', range.start, 30, 720)
    expect(dateAtScrollCenter(left, 720, range.start, 30)).toBe('2026-08-24')
  })
})
