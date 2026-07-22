import rawTracks from '@/data/tracks.json'

/* ------------------------------------------------------------------ */
/* Types & raw data                                                    */
/* ------------------------------------------------------------------ */

export interface Track {
  track: string
  bpm: number
  key: string
  brightness: 'Bright/Aggressive' | 'Warm/Dark'
  energy_density: number
  alpha: number
  structural_velocity: number
  market_modularity: number
  hpi: number
  verdict: string
}

export const TRACKS: Track[] = rawTracks as Track[]

export const TOTAL_TRACKS = TRACKS.length // 198

/* ------------------------------------------------------------------ */
/* Strategy bucketing (design.md §2 — rules applied in order)          */
/* ------------------------------------------------------------------ */

export type Bucket = 'ACQUIRE' | 'PITCH+LICENSE' | 'PITCH' | 'LICENSE' | 'ANALYZE'

export function bucketOf(verdict: string): Bucket {
  const v = verdict.toLowerCase()
  if (v.includes('acquisition')) return 'ACQUIRE'
  if (v.includes('playlist') && (v.includes('licensing') || v.includes('monetization')))
    return 'PITCH+LICENSE'
  if (v.includes('playlist')) return 'PITCH'
  if (v.includes('licensing') || v.includes('monetization')) return 'LICENSE'
  return 'ANALYZE'
}

export const BUCKETS: Bucket[] = ['ACQUIRE', 'PITCH', 'PITCH+LICENSE', 'LICENSE', 'ANALYZE']

/** Donut order — clockwise from 12 o'clock, descending count (home.md §3b) */
export const DONUT_ORDER: Bucket[] = ['PITCH', 'ANALYZE', 'ACQUIRE', 'PITCH+LICENSE', 'LICENSE']

export const BUCKET_COLORS: Record<Bucket, string> = {
  ACQUIRE: '#E8A33D',
  PITCH: '#C9A45C',
  'PITCH+LICENSE': '#B87333',
  LICENSE: '#A85B32',
  ANALYZE: '#6E6353',
}

const bucketCountsInit: Record<Bucket, number> = {
  ACQUIRE: 0,
  PITCH: 0,
  'PITCH+LICENSE': 0,
  LICENSE: 0,
  ANALYZE: 0,
}

export const BUCKET_COUNTS: Record<Bucket, number> = TRACKS.reduce((acc, t) => {
  acc[bucketOf(t.verdict)] += 1
  return acc
}, { ...bucketCountsInit })

/* ------------------------------------------------------------------ */
/* Headline aggregates (QA: 198 · 8.34 · 41 · 117.2 · 153 / 77.3%)     */
/* ------------------------------------------------------------------ */

export const AVG_HPI = TRACKS.reduce((s, t) => s + t.hpi, 0) / TOTAL_TRACKS
export const AVG_BPM = TRACKS.reduce((s, t) => s + t.bpm, 0) / TOTAL_TRACKS
export const ACQUIRE_COUNT = BUCKET_COUNTS.ACQUIRE
export const RED_ZONE_MIN = 8.5
export const RED_ZONE_COUNT = TRACKS.filter((t) => t.hpi >= RED_ZONE_MIN).length
export const RED_ZONE_PCT = (RED_ZONE_COUNT / TOTAL_TRACKS) * 100

export const BPM_MIN = Math.min(...TRACKS.map((t) => t.bpm))
export const BPM_MAX = Math.max(...TRACKS.map((t) => t.bpm))
export const HPI_MIN = Math.min(...TRACKS.map((t) => t.hpi))
export const HPI_MAX = Math.max(...TRACKS.map((t) => t.hpi))

/* Metric display ranges (design.md §2) */
export const METRIC_RANGES = {
  energy_density: { min: 1.0, max: 7.5 },
  alpha: { min: 7.2, max: 8.5 },
  structural_velocity: { min: 1.0, max: 10.0 },
  market_modularity: { min: 6.5, max: 8.5 },
} as const

/* ------------------------------------------------------------------ */
/* HPI histogram — 8 bins of 0.5 over 5.0–9.0 (home.md §3a)            */
/* ------------------------------------------------------------------ */

export interface HistBin {
  lo: number
  hi: number
  count: number
}

export const HIST_BINS: HistBin[] = Array.from({ length: 8 }, (_, i) => {
  const lo = 5.0 + i * 0.5
  return { lo, hi: lo + 0.5, count: 0 }
})

for (const t of TRACKS) {
  const idx = Math.min(7, Math.max(0, Math.floor((t.hpi - 5.0) / 0.5)))
  HIST_BINS[idx].count += 1
}

/* ------------------------------------------------------------------ */
/* Key census (home.md §3d)                                            */
/* ------------------------------------------------------------------ */

export const KEYS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'] as const
export type KeyName = (typeof KEYS)[number]

export const KEY_COUNTS: { key: KeyName; count: number }[] = KEYS.map((k) => ({
  key: k,
  count: TRACKS.filter((t) => t.key === k).length,
}))

export const ANCHOR_KEY: KeyName = KEY_COUNTS.reduce((a, b) => (b.count > a.count ? b : a)).key

/* ------------------------------------------------------------------ */
/* Brightness series                                                   */
/* ------------------------------------------------------------------ */

export const BRIGHT_COUNT = TRACKS.filter((t) => t.brightness === 'Bright/Aggressive').length
export const WARM_COUNT = TOTAL_TRACKS - BRIGHT_COUNT

/* ------------------------------------------------------------------ */
/* Top prospects (home.md §4 — deterministic ranking)                  */
/* ------------------------------------------------------------------ */

export function compareTracksRank(a: Track, b: Track): number {
  if (b.hpi !== a.hpi) return b.hpi - a.hpi
  if (b.market_modularity !== a.market_modularity) return b.market_modularity - a.market_modularity
  if (b.alpha !== a.alpha) return b.alpha - a.alpha
  return a.track.localeCompare(b.track)
}

export const TOP_PROSPECTS: Track[] = [...TRACKS].sort(compareTracksRank).slice(0, 6)

/* ------------------------------------------------------------------ */
/* Formatting helpers                                                  */
/* ------------------------------------------------------------------ */

export const truncate = (s: string, n: number) => (s.length > n ? `${s.slice(0, n - 1)}…` : s)
