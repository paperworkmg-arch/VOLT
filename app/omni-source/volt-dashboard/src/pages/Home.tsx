import { useCallback, useState } from 'react'
import Analyzers from '@/sections/Analyzers'
import Hero from '@/sections/Hero'
import KpiStrip from '@/sections/KpiStrip'
import Ledger from '@/sections/Ledger'
import Pipeline from '@/sections/Pipeline'
import Prospects from '@/sections/Prospects'
import AgentsSection from '@/sections/Agents'
import TasksSection from '@/sections/Tasks'
import SwarmSection from '@/sections/Swarm'
import ActivitySection from '@/sections/Activity'
import SamplesSection from '@/sections/Samples'
import VaultSection from '@/sections/Vault'
import SystemSection from '@/sections/System'
import { useCatalog } from '@/lib/catalog-context'
import type { CrossFilter } from '@/lib/crossfilter'
import type { LedgerFilters } from '@/lib/filters'
import { DEFAULT_FILTERS } from '@/lib/filters'
import { scrollToTarget } from '@/lib/motion'

/** Volt Records catalog intelligence console — the single dashboard page. */
export default function Home() {
  const { tracks } = useCatalog()
  const [filters, setFilters] = useState<LedgerFilters>(DEFAULT_FILTERS)

  const handleCrossFilter = useCallback((cf: CrossFilter) => {
    setFilters((prev) => {
      switch (cf.kind) {
        case 'hpi':
          return { ...prev, hpiRange: [cf.lo, cf.hi], source: cf.label, highlight: null }
        case 'strategy':
          return { ...prev, strategy: cf.bucket, source: cf.bucket, highlight: null }
        case 'key':
          return { ...prev, key: cf.key, source: `KEY ${cf.key}`, highlight: null }
        case 'tone':
          return {
            ...prev,
            tone: cf.tone,
            source:
              cf.tone === 'ALL' ? null : cf.tone === 'Bright/Aggressive' ? 'BRIGHT/AGGRESSIVE' : 'WARM/DARK',
            highlight: null,
          }
        case 'track':
          return { ...prev, search: cf.name, highlight: cf.name }
      }
    })
    scrollToTarget('#ledger', -64)
  }, [])

  return (
    <>
      <Hero />
      <div className="mx-auto flex max-w-console flex-col gap-16 px-5 pt-16 md:gap-24 md:px-8 md:pt-24">
        <KpiStrip />
        <Analyzers tracks={tracks} filters={filters} onCrossFilter={handleCrossFilter} />
        <Prospects onCrossFilter={handleCrossFilter} />
        <AgentsSection />
        <TasksSection />
        <SwarmSection />
        <SamplesSection />
        <VaultSection />
        <Ledger filters={filters} onFiltersChange={setFilters} />
        <ActivitySection />
        <SystemSection />
        <Pipeline />
      </div>
    </>
  )
}
