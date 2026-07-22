import { useState } from 'react'
import { useSwarmRuns } from '@/hooks/use-swarm'
import { runSwarm } from '@/lib/api'
import { useQueryClient } from '@tanstack/react-query'

export default function SwarmSection() {
  const { data: runs } = useSwarmRuns()
  const [objective, setObjective] = useState('')
  const [running, setRunning] = useState(false)
  const qc = useQueryClient()

  const handleRun = async () => {
    if (!objective.trim()) return
    setRunning(true)
    try { await runSwarm(objective) } catch {}
    setObjective('')
    setRunning(false)
    qc.invalidateQueries({ queryKey: ['swarm-runs'] })
  }

  return (
    <section id="swarm" className="space-y-4">
      <h2 className="font-display text-sm uppercase tracking-[0.12em] text-ink-1">SWARM</h2>
      <div className="flex gap-2">
        <input
          value={objective}
          onChange={(e) => setObjective(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleRun()}
          placeholder="Enter objective..."
          className="flex-1 rounded border border-line-strong bg-bg-1 px-3 py-2 font-mono text-xs text-ink-2 placeholder:text-ink-5 focus:border-amber focus:outline-none"
        />
        <button
          onClick={handleRun}
          disabled={running || !objective.trim()}
          className="rounded border border-amber bg-amber/10 px-4 py-2 font-mono text-[10px] uppercase tracking-[0.1em] text-amber hover:bg-amber/20 transition-colors disabled:opacity-40"
        >
          {running ? 'Running...' : 'Decompose & Execute'}
        </button>
      </div>
      <div className="overflow-x-auto rounded-[4px] border border-line">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-line bg-bg-1">
              <th className="px-3 py-2 font-mono text-[9px] uppercase tracking-[0.14em] text-ink-4">Objective</th>
              <th className="px-3 py-2 font-mono text-[9px] uppercase tracking-[0.14em] text-ink-4">Status</th>
              <th className="px-3 py-2 font-mono text-[9px] uppercase tracking-[0.14em] text-ink-4">Started</th>
              <th className="px-3 py-2 font-mono text-[9px] uppercase tracking-[0.14em] text-ink-4">Agents</th>
            </tr>
          </thead>
          <tbody>
            {runs?.map((r) => (
              <tr key={r.id} className="border-b border-line last:border-0 hover:bg-bg-1/50 transition-colors">
                <td className="px-3 py-2 font-mono text-xs text-ink-2 max-w-[200px] truncate">{r.objective}</td>
                <td className="px-3 py-2">
                  <span className={`font-mono text-[10px] uppercase ${r.status === 'completed' ? 'text-emerald-400' : r.status === 'failed' ? 'text-red-400' : 'text-amber'}`}>
                    {r.status}
                  </span>
                </td>
                <td className="px-3 py-2 font-mono text-[10px] text-ink-4">{r.started_at?.slice(0, 16)}</td>
                <td className="px-3 py-2 font-mono text-[10px] text-ink-4">{r.agents_used || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
