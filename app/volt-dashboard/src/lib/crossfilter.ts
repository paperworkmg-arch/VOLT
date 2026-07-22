import type { Bucket, KeyName } from './catalog'
import type { ToneFilter } from './filters'

/** Cross-filter intents emitted by charts and prospect cards. */
export type CrossFilter =
  | { kind: 'hpi'; lo: number; hi: number; label: string }
  | { kind: 'strategy'; bucket: Bucket }
  | { kind: 'key'; key: KeyName }
  | { kind: 'tone'; tone: ToneFilter }
  | { kind: 'track'; name: string }
