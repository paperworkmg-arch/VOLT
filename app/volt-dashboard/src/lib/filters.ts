import type { Bucket, KeyName, Track } from './catalog'
import { bucketOf } from './catalog'

export type ToneFilter = 'ALL' | 'Bright/Aggressive' | 'Warm/Dark'

export interface LedgerFilters {
  search: string
  tone: ToneFilter
  strategy: 'ALL' | Bucket
  key: 'ALL' | KeyName
  hpiRange: [number, number]
  /** label shown on the cross-filter chip when a chart drove the filter */
  source: string | null
  /** track name to flash-highlight in the ledger (scatter/prospect deep-link) */
  highlight: string | null
}

export const DEFAULT_FILTERS: LedgerFilters = {
  search: '',
  tone: 'ALL',
  strategy: 'ALL',
  key: 'ALL',
  hpiRange: [5.0, 9.0],
  source: null,
  highlight: null,
}

export function filtersActive(f: LedgerFilters): boolean {
  return (
    f.search.trim() !== '' ||
    f.tone !== 'ALL' ||
    f.strategy !== 'ALL' ||
    f.key !== 'ALL' ||
    f.hpiRange[0] > 5.0 + 1e-9 ||
    f.hpiRange[1] < 9.0 - 1e-9 ||
    f.source !== null ||
    f.highlight !== null
  )
}

export function applyFilters(tracks: Track[], f: LedgerFilters): Track[] {
  const q = f.search.trim().toLowerCase()
  return tracks.filter((t) => {
    if (q && !t.track.toLowerCase().includes(q) && !t.verdict.toLowerCase().includes(q)) return false
    if (f.tone !== 'ALL' && t.brightness !== f.tone) return false
    if (f.strategy !== 'ALL' && bucketOf(t.verdict) !== f.strategy) return false
    if (f.key !== 'ALL' && t.key !== f.key) return false
    if (t.hpi < f.hpiRange[0] - 1e-9 || t.hpi > f.hpiRange[1] + 1e-9) return false
    return true
  })
}

export type SortKey =
  | 'track'
  | 'bpm'
  | 'key'
  | 'brightness'
  | 'energy_density'
  | 'alpha'
  | 'structural_velocity'
  | 'market_modularity'
  | 'hpi'
  | 'verdict'

export type SortDir = 'asc' | 'desc'

export function sortTracks(tracks: Track[], key: SortKey, dir: SortDir): Track[] {
  const sign = dir === 'asc' ? 1 : -1
  return [...tracks].sort((a, b) => {
    let cmp = 0
    switch (key) {
      case 'track':
        cmp = a.track.localeCompare(b.track)
        break
      case 'key':
        cmp = a.key.localeCompare(b.key)
        break
      case 'brightness':
        cmp = a.brightness.localeCompare(b.brightness)
        break
      case 'verdict':
        cmp = bucketOf(a.verdict).localeCompare(bucketOf(b.verdict))
        break
      default:
        cmp = a[key] - b[key]
    }
    if (cmp !== 0) return cmp * sign
    /* deterministic tiebreak — rank rule (design default sort) */
    if (b.hpi !== a.hpi) return b.hpi - a.hpi
    if (b.market_modularity !== a.market_modularity) return b.market_modularity - a.market_modularity
    if (b.alpha !== a.alpha) return b.alpha - a.alpha
    return a.track.localeCompare(b.track)
  })
}
