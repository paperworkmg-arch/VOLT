import { useAgents } from '@/hooks/use-agents'
import { toggleAgent } from '@/lib/api'
import { useQueryClient } from '@tanstack/react-query'

const STATUS_COLORS: Record<string, string> = {
  idle: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  working: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  paused: 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30',
  failed: 'bg-red-500/20 text-red-400 border-red-500/30',
}

export default function AgentsSection() {
  const { data: agents } = useAgents()
  const qc = useQueryClient()

  const handleToggle = async (id: number) => {
    await toggleAgent(id)
    qc.invalidateQueries({ queryKey: ['agents'] })
  }

  return (
    <section id="agents" className="space-y-4">
      <h2 className="font-display text-sm uppercase tracking-[0.12em] text-ink-1">AGENTS</h2>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {agents?.map((a) => (
          <div key={a.id} className="rounded-[4px] border border-line bg-bg-1 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="font-display text-sm text-ink-1">{a.name}</span>
                <span className="ml-2 font-mono text-[10px] uppercase tracking-[0.1em] text-ink-4">{a.role}</span>
              </div>
              <span className={`rounded-full border px-2 py-0.5 font-mono text-[9px] uppercase ${STATUS_COLORS[a.status] || STATUS_COLORS.idle}`}>
                {a.status}
              </span>
            </div>
            <p className="font-mono text-[10px] text-ink-4 truncate">{a.model}</p>
            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] text-ink-3">{a.tasks_completed} tasks</span>
              <button
                onClick={() => handleToggle(a.id)}
                className="rounded border border-line-strong px-2 py-1 font-mono text-[9px] uppercase text-ink-2 hover:border-amber hover:text-amber transition-colors"
              >
                {a.status === 'paused' ? 'RESUME' : 'PAUSE'}
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
