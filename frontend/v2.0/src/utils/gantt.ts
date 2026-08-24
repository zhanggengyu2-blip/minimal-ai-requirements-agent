export type GanttScale = 'day' | 'week' | 'month'

export interface GanttHeaderBand {
  key: string
  label: string
  startIndex: number
  dayCount: number
}

export interface GanttRange {
  start: string
  end: string
  dayCount: number
}

export interface GanttBarGeometry {
  left: number
  width: number
  durationDays: number
}

const DAY_MS = 86_400_000

export const scaleDayWidth: Record<GanttScale, number> = {
  day: 56,
  week: 30,
  month: 12,
}

export const dateToOrdinal = (value: string): number => {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!match) throw new Error(`Invalid business date: ${value}`)
  const year = Number(match[1])
  const month = Number(match[2])
  const day = Number(match[3])
  const ordinal = Math.floor(Date.UTC(year, month - 1, day) / DAY_MS)
  if (ordinalToDate(ordinal) !== value) throw new Error(`Invalid business date: ${value}`)
  return ordinal
}

export const ordinalToDate = (ordinal: number): string => {
  const date = new Date(ordinal * DAY_MS)
  return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}-${String(date.getUTCDate()).padStart(2, '0')}`
}

export const addBusinessDays = (value: string, days: number) =>
  ordinalToDate(dateToOrdinal(value) + days)

export const businessToday = (now = new Date()): string =>
  `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`

export const buildGanttRange = (dates: Array<string | null | undefined>, today = businessToday()): GanttRange => {
  const ordinals = dates.filter((value): value is string => Boolean(value)).map(dateToOrdinal)
  const todayOrdinal = dateToOrdinal(today)
  const minimum = Math.min(todayOrdinal - 180, ...(ordinals.map((value) => value - 35)))
  const maximum = Math.max(todayOrdinal + 180, ...(ordinals.map((value) => value + 65)))
  return {
    start: ordinalToDate(minimum),
    end: ordinalToDate(maximum),
    dayCount: maximum - minimum + 1,
  }
}

const monthLabel = (ordinal: number) => {
  const date = new Date(ordinal * DAY_MS)
  return `${date.getUTCFullYear()}年${date.getUTCMonth() + 1}月`
}
const yearLabel = (ordinal: number) => `${new Date(ordinal * DAY_MS).getUTCFullYear()}年`
const shortDate = (ordinal: number) => {
  const date = new Date(ordinal * DAY_MS)
  return `${date.getUTCMonth() + 1}/${date.getUTCDate()}`
}
const mondayOrdinal = (ordinal: number) => {
  const day = new Date(ordinal * DAY_MS).getUTCDay()
  return ordinal - (day === 0 ? 6 : day - 1)
}

const groupBands = (
  startOrdinal: number,
  dayCount: number,
  keyFor: (ordinal: number) => string,
  labelFor: (ordinal: number) => string,
): GanttHeaderBand[] => {
  const bands: GanttHeaderBand[] = []
  for (let index = 0; index < dayCount; index += 1) {
    const ordinal = startOrdinal + index
    const key = keyFor(ordinal)
    const previous = bands[bands.length - 1]
    if (previous?.key === key) previous.dayCount += 1
    else bands.push({ key, label: labelFor(ordinal), startIndex: index, dayCount: 1 })
  }
  return bands
}

export const buildHeaderBands = (range: GanttRange, scale: GanttScale) => {
  const startOrdinal = dateToOrdinal(range.start)
  const primary = groupBands(
    startOrdinal,
    range.dayCount,
    scale === 'month'
      ? (ordinal) => String(new Date(ordinal * DAY_MS).getUTCFullYear())
      : (ordinal) => ordinalToDate(ordinal).slice(0, 7),
    scale === 'month' ? yearLabel : monthLabel,
  )
  const secondary = scale === 'day'
    ? groupBands(startOrdinal, range.dayCount, ordinalToDate, (ordinal) => shortDate(ordinal))
    : scale === 'week'
      ? groupBands(
          startOrdinal,
          range.dayCount,
          (ordinal) => String(mondayOrdinal(ordinal)),
          (ordinal) => `${shortDate(mondayOrdinal(ordinal))}–${shortDate(mondayOrdinal(ordinal) + 6)}`,
        )
      : groupBands(
          startOrdinal,
          range.dayCount,
          (ordinal) => ordinalToDate(ordinal).slice(0, 7),
          monthLabel,
        )
  return { primary, secondary }
}

export const ganttBarGeometry = (
  startDate: string | null | undefined,
  endDate: string | null | undefined,
  rangeStart: string,
  dayWidth: number,
): GanttBarGeometry | null => {
  if (!startDate || !endDate) return null
  const start = dateToOrdinal(startDate)
  const end = dateToOrdinal(endDate)
  if (end < start) return null
  const durationDays = end - start + 1
  return {
    left: (start - dateToOrdinal(rangeStart)) * dayWidth + 2,
    width: Math.max(8, durationDays * dayWidth - 4),
    durationDays,
  }
}

export const scrollLeftForDate = (
  value: string,
  rangeStart: string,
  dayWidth: number,
  viewportWidth: number,
) => Math.max(0, (dateToOrdinal(value) - dateToOrdinal(rangeStart) + 0.5) * dayWidth - viewportWidth / 2)

export const dateAtScrollCenter = (
  scrollLeft: number,
  viewportWidth: number,
  rangeStart: string,
  dayWidth: number,
) => addBusinessDays(rangeStart, Math.max(0, Math.floor((scrollLeft + viewportWidth / 2) / dayWidth)))
