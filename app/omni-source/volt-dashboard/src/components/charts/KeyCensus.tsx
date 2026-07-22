import { useMemo, useRef } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { useGSAP } from '@gsap/react'
import ChartTip from '@/components/ChartTip'
import Panel from '@/components/Panel'
import type { Track } from '@/lib/catalog'
import type { LedgerFilters } from '@/lib/filters'
import type { CrossFilter } from '@/lib/crossfilter'
import { prefersReducedMotion } from '@/lib/motion'

gsap.registerPlugin(ScrollTrigger, useGSAP)

const W = 340
const ROW = 22
const BAR_H = 14
const MT = 6
const LABEL_W = 30
const MAX_BAR = 196

interface Props {
  tracks: Track[]
  filters: LedgerFilters
  onCrossFilter: (cf: CrossFilter) => void
}

/** §3d — key signature census, 12 horizontal bars, chromatic order. */
export default function KeyCensus({ tracks, filters, onCrossFilter }: Props) {
  const root = useRef<HTMLDivElement>(null)
  const TOTAL_TRACKS = tracks.length

  const KEYS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'] as const

  const KEY_COUNTS = useMemo(
    () => KEYS.map((k) => ({ key: k, count: tracks.filter((t) => t.key === k).length })),
    [tracks],
  )

  const H = MT * 2 + KEY_COUNTS.length * ROW
  const max = Math.max(...KEY_COUNTS.map((k) => k.count))
  const ANCHOR_KEY = KEY_COUNTS.reduce((a, b) => (b.count > a.count ? b : a), KEY_COUNTS[0])?.key ?? 'C'

  useGSAP(
    () => {
      const el = root.current
      if (!el) return
      const bars = el.querySelectorAll<SVGRectElement>('.key-bar')
      const counts = el.querySelectorAll<SVGTextElement>('.key-count')
      if (prefersReducedMotion()) {
        counts.forEach((c, i) => {
          c.textContent = String(KEY_COUNTS[i].count)
        })
        return
      }
      gsap.set(bars, { scaleX: 0, transformOrigin: '0% 50%', transformBox: 'fill-box' })
      const tl = gsap.timeline({ paused: true })
      tl.to(bars, { scaleX: 1, duration: 0.6, ease: 'expo.out', stagger: 0.04 }, 0)
      counts.forEach((c, i) => {
        const state = { v: 0 }
        tl.to(
          state,
          {
            v: KEY_COUNTS[i].count,
            duration: 0.6,
            ease: 'expo.out',
            snap: { v: 1 },
            onUpdate: () => {
              c.textContent = String(Math.round(state.v))
            },
          },
          i * 0.04,
        )
      })
      const st = ScrollTrigger.create({ trigger: el, start: 'top 75%', once: true, onEnter: () => tl.play() })
      return () => {
        st.kill()
        tl.kill()
      }
    },
    { scope: root, dependencies: [tracks] },
  )

  return (
    <div ref={root} className="order-4 col-span-12 lg:order-4 lg:col-span-5">
      <Panel title="KEY CENSUS" meta="12 KEYS" className="h-full">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="w-full"
          role="img"
          aria-label={`Key signature census across ${TOTAL_TRACKS} tracks; modal key ${ANCHOR_KEY} with ${max} tracks`}
        >
          {KEY_COUNTS.map(({ key, count }, i) => {
            const y = MT + i * ROW
            const w = Math.max(2, (count / max) * MAX_BAR)
            const anchor = key === ANCHOR_KEY
            const active = filters.key === key
            const bar = (
              <g
                key={key}
                className="cursor-pointer"
                onClick={() => onCrossFilter({ kind: 'key', key })}
              >
                <title>{`KEY ${key} — ${count} TRACKS (${TOTAL_TRACKS > 0 ? ((count / TOTAL_TRACKS) * 100).toFixed(1) : '0.0'}%)`}</title>
                <text x="0" y={y + 11} fill="#B3A58D" fontSize="11" fontFamily="'JetBrains Mono', monospace">
                  {key}
                </text>
                <rect
                  className="key-bar transition-[fill] duration-150 hover:fill-amber-hi"
                  x={LABEL_W}
                  y={y}
                  width={w}
                  height={BAR_H}
                  rx="1"
                  fill={anchor ? '#E8A33D' : '#B87333'}
                  fillOpacity={anchor ? 1 : 0.75}
                  stroke={active ? '#F5C15C' : 'none'}
                  strokeWidth={active ? 1 : 0}
                  style={anchor ? { filter: 'drop-shadow(0 0 6px rgba(232,163,61,0.4))' } : undefined}
                />
                <text
                  className="key-count"
                  x={LABEL_W + w + 6}
                  y={y + 11}
                  fill="#7D7160"
                  fontSize="10"
                  fontFamily="'JetBrains Mono', monospace"
                >
                  {count}
                </text>
                {anchor && (
                  <text
                    x={LABEL_W + w + 28}
                    y={y + 10}
                    fill="#E8A33D"
                    fontSize="8"
                    fontFamily="'JetBrains Mono', monospace"
                    letterSpacing="1"
                  >
                    ANCHOR KEY
                  </text>
                )}
              </g>
            )
            return (
              <ChartTip key={key} label={`KEY ${key} — ${count} TRACKS (${TOTAL_TRACKS > 0 ? ((count / TOTAL_TRACKS) * 100).toFixed(1) : '0.0'}%)`}>
                {bar}
              </ChartTip>
            )
          })}
        </svg>
      </Panel>
    </div>
  )
}
