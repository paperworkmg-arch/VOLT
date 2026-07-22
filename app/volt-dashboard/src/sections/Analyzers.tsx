import SectionHeader from '@/components/SectionHeader'
import BpmHpiScatter from '@/components/charts/BpmHpiScatter'
import HpiHistogram from '@/components/charts/HpiHistogram'
import KeyCensus from '@/components/charts/KeyCensus'
import StrategyDonut from '@/components/charts/StrategyDonut'
import type { Track } from '@/lib/catalog'
import type { LedgerFilters } from '@/lib/filters'
import type { CrossFilter } from '@/lib/crossfilter'

interface Props {
  tracks: Track[]
  filters: LedgerFilters
  onCrossFilter: (cf: CrossFilter) => void
}

/** §3 — analyzer grid: 7+5 / 7+5 on desktop, big charts first when stacked. */
export default function Analyzers({ tracks, filters, onCrossFilter }: Props) {
  const total = tracks.length
  return (
    <section id="analyzers" aria-label="Signal analysis" className="scroll-mt-20">
      <SectionHeader
        overline="02 / ANALYZERS"
        title="SIGNAL ANALYSIS"
        descriptor={`Distribution, tempo correlation, key signature census and strategy mix across ${total} records.`}
      />
      <div className="grid grid-cols-12 gap-4">
        <HpiHistogram tracks={tracks} filters={filters} onCrossFilter={onCrossFilter} />
        <StrategyDonut tracks={tracks} filters={filters} onCrossFilter={onCrossFilter} />
        <BpmHpiScatter tracks={tracks} filters={filters} onCrossFilter={onCrossFilter} />
        <KeyCensus tracks={tracks} filters={filters} onCrossFilter={onCrossFilter} />
      </div>
    </section>
  )
}
