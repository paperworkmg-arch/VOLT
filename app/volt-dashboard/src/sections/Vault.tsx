import { useState } from 'react'
import { useVaultEntries, useVaultStats, useVaultSearch, useExtractionHistory } from '@/hooks/use-vault'

const CATEGORIES = ['all', 'music_ip', 'crm', 'sops', 'extractions']

export default function VaultSection() {
  const [cat, setCat] = useState('')
  const [search, setSearch] = useState('')
  const { data: entries } = useVaultEntries(cat || undefined)
  const { data: stats } = useVaultStats()
  const { data: searchResults } = useVaultSearch(search)
  const { data: extractions } = useExtractionHistory()

  const display = search.length > 1 ? searchResults : entries

  return (
    <section id="vault" className="space-y-4">
      <h2 className="font-display text-sm uppercase tracking-[0.12em] text-ink-1">VAULT</h2>

      {stats && (
        <div className="flex gap-3 text-center">
          <div className="rounded border border-line bg-bg-1 px-3 py-2">
            <div className="font-mono text-lg text-amber">{stats.total_entries}</div>
            <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-ink-4">Entries</div>
          </div>
          <div className="rounded border border-line bg-bg-1 px-3 py-2">
            <div className="font-mono text-lg text-amber">{stats.total_extractions}</div>
            <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-ink-4">Extractions</div>
          </div>
        </div>
      )}

      {/* Category tabs */}
      <div className="flex gap-1.5 flex-wrap">
        {CATEGORIES.map((c) => (
          <button
            key={c}
            onClick={() => { setCat(c === 'all' ? '' : c); setSearch('') }}
            className={`rounded border px-2.5 py-1 font-mono text-[9px] uppercase tracking-[0.1em] transition-colors ${
              (c === 'all' && !cat) || cat === c
                ? 'border-amber bg-amber/10 text-amber'
                : 'border-line text-ink-4 hover:border-line-strong hover:text-ink-2'
            }`}
          >
            {c}
          </button>
        ))}
      </div>

      <input
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Search vault..."
        className="w-full rounded border border-line-strong bg-bg-1 px-3 py-2 font-mono text-xs text-ink-2 placeholder:text-ink-5 focus:border-amber focus:outline-none"
      />

      <div className="space-y-2 max-h-[350px] overflow-y-auto pr-1">
        {display?.map((e) => (
          <div key={e.id} className="rounded border border-line bg-bg-1 p-3 space-y-1">
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs text-ink-2">{e.title}</span>
              <span className="rounded border border-line px-1.5 py-0.5 font-mono text-[8px] uppercase text-ink-4">{e.category}</span>
            </div>
            <p className="font-mono text-[10px] text-ink-4 line-clamp-2">{e.content?.slice(0, 200)}</p>
            <span className="font-mono text-[9px] text-ink-5">{e.created_at?.slice(0, 16)}</span>
          </div>
        ))}
      </div>

      {extractions && extractions.length > 0 && (
        <div className="space-y-2">
          <h3 className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-3">Recent Extractions</h3>
          {extractions.slice(0, 5).map((e, i) => (
            <div key={i} className="rounded border border-line bg-bg-1 px-3 py-2 flex items-center justify-between">
              <span className="font-mono text-[10px] text-ink-3">{e.run_date?.slice(0, 10) || '—'}</span>
              <span className={`font-mono text-[9px] uppercase ${e.status === 'completed' ? 'text-emerald-400' : 'text-amber'}`}>{e.status}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
