import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

interface Lead {
  id: number; name: string; email: string; city: string; company: string
  status: string; source: string; sub_library: string; linkedin_url: string
  created_at: string
}
interface LeadStats { total: number; by_status: Record<string,number>; by_source: Record<string,number> }

const STATUS_COLORS: Record<string, string> = {
  'SCRAPED': 'border-zinc-500/30 text-zinc-400',
  'MUSIC_LIBRARY_TARGET': 'border-amber/30 text-amber',
  'PENDING VERIFICATION': 'border-orange-400/30 text-orange-400',
  'PITCHED': 'border-cyan-400/30 text-cyan-400',
  'CLOSED': 'border-emerald-500/30 text-emerald-400',
}

const SOURCE_ICONS: Record<string, string> = {
  'MUSIC_LIBRARY_TARGET': '🎵',
  'SCRAPED': '🤖',
  'manual': '✏️',
  'PENDING VERIFICATION': '📧',
}

export default function LeadsSection() {
  const [filter, setFilter] = useState('')
  const qc = useQueryClient()

  const { data: leadsData } = useQuery<{leads: Lead[]; total: number}>({
    queryKey: ['leads', filter],
    queryFn: () => fetch(`/api/leads${filter ? `?status=${filter}` : ''}`).then(r => r.json()),
  })
  const { data: stats } = useQuery<LeadStats>({
    queryKey: ['lead-stats'],
    queryFn: () => fetch('/api/leads/stats').then(r => r.json()),
  })

  const handleScan = async () => {
    await fetch('/api/leads/scan-library', { method: 'POST' })
    setTimeout(() => qc.invalidateQueries({ queryKey: ['leads'] }), 5000)
  }
  const handleAudit = async () => {
    await fetch('/api/leads/audit-payments', { method: 'POST' })
    setTimeout(() => qc.invalidateQueries({ queryKey: ['leads'] }), 5000)
  }

  return (
    <section id="leads" className="space-y-4">
      <h2 className="font-display text-sm uppercase tracking-[0.12em] text-ink-1">LEAD PIPELINE</h2>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded border border-line bg-bg-1 px-3 py-2 text-center">
            <div className="font-mono text-lg text-amber tabular-nums">{stats.total}</div>
            <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-ink-4">TOTAL</div>
          </div>
          {Object.entries(stats.by_status || {}).slice(0, 3).map(([status, count]) => (
            <div key={status} className="rounded border border-line bg-bg-1 px-3 py-2 text-center">
              <div className="font-mono text-lg text-ink-2 tabular-nums">{count}</div>
              <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-ink-4 truncate">{status}</div>
            </div>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2 flex-wrap">
        <button onClick={handleScan} className="rounded border border-amber/30 bg-amber/10 px-3 py-1.5 font-mono text-[9px] uppercase tracking-[0.1em] text-amber hover:bg-amber/20 transition-colors">
          Scan Music Libraries
        </button>
        <button onClick={handleAudit} className="rounded border border-cyan-400/30 bg-cyan-400/10 px-3 py-1.5 font-mono text-[9px] uppercase tracking-[0.1em] text-cyan-400 hover:bg-cyan-400/20 transition-colors">
          Audit Missed Payments
        </button>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="rounded border border-line-strong bg-bg-1 px-2 py-1 font-mono text-[10px] text-ink-2"
        >
          <option value="">All Statuses</option>
          <option value="SCRAPED">Scraped</option>
          <option value="MUSIC_LIBRARY_TARGET">Music Library</option>
          <option value="PENDING VERIFICATION">Pending</option>
          <option value="PITCHED">Pitched</option>
          <option value="CLOSED">Closed</option>
        </select>
      </div>

      {/* Leads table */}
      <div className="overflow-x-auto rounded-[4px] border border-line max-h-[400px] overflow-y-auto">
        <table className="w-full text-left">
          <thead className="sticky top-0 bg-bg-1">
            <tr className="border-b border-line">
              <th className="px-3 py-2 font-mono text-[9px] uppercase tracking-[0.14em] text-ink-4">Name</th>
              <th className="px-3 py-2 font-mono text-[9px] uppercase tracking-[0.14em] text-ink-4">Company</th>
              <th className="px-3 py-2 font-mono text-[9px] uppercase tracking-[0.14em] text-ink-4">Status</th>
              <th className="px-3 py-2 font-mono text-[9px] uppercase tracking-[0.14em] text-ink-4">Source</th>
              <th className="px-3 py-2 font-mono text-[9px] uppercase tracking-[0.14em] text-ink-4">City</th>
            </tr>
          </thead>
          <tbody>
            {leadsData?.leads?.map((l) => (
              <tr key={l.id} className="border-b border-line last:border-0 hover:bg-bg-1/50 transition-colors">
                <td className="px-3 py-2">
                  <div className="font-mono text-xs text-ink-2">{l.name}</div>
                  <div className="font-mono text-[9px] text-ink-5 truncate max-w-[150px]">{l.email}</div>
                </td>
                <td className="px-3 py-2 font-mono text-[10px] text-ink-3">{l.company || l.sub_library || '—'}</td>
                <td className="px-3 py-2">
                  <span className={`rounded border px-1.5 py-0.5 font-mono text-[8px] uppercase ${STATUS_COLORS[l.status] || 'border-line text-ink-4'}`}>
                    {l.status}
                  </span>
                </td>
                <td className="px-3 py-2">
                  <span className="font-mono text-[10px]">{SOURCE_ICONS[l.source] || '⚙️'} {l.source}</span>
                </td>
                <td className="px-3 py-2 font-mono text-[10px] text-ink-4">{l.city || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
