import { useVoltAgents } from '@/hooks/use-volt-agents'

const COLOR_MAP: Record<string, string> = {
  amber: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  emerald: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  blue: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  violet: 'bg-violet-500/20 text-violet-400 border-violet-500/30',
  green: 'bg-green-500/20 text-green-400 border-green-500/30',
  orange: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  pink: 'bg-pink-500/20 text-pink-400 border-pink-500/30',
  cyan: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
}

export default function VoltAgents() {
  const { agents, pipeline, loading, runAgent, stopAgent } = useVoltAgents()

  return (
    <section id="volt-agents" className="space-y-6">
      <h2 className="font-display text-sm uppercase tracking-[0.12em] text-ink-1">VOLT RECORDS AGENTS</h2>
      
      {/* Pipeline Stats */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
        {[
          { label: 'INCOMING', value: pipeline.incoming_leads, icon: 'fa-solid fa-inbox' },
          { label: 'PITCHES', value: pipeline.outbound_pitches, icon: 'fa-solid fa-paper-plane' },
          { label: 'QUEUED', value: pipeline.send_queue, icon: 'fa-solid fa-clock' },
          { label: 'SENT', value: pipeline.sent, icon: 'fa-solid fa-check' },
          { label: 'CLOSED', value: pipeline.closed_deals, icon: 'fa-solid fa-handshake' },
          { label: 'SKIPPED', value: pipeline.skipped, icon: 'fa-solid fa-forward' },
        ].map((stat) => (
          <div key={stat.label} className="rounded-[4px] border border-line bg-bg-1 p-3 text-center">
            <i className={`${stat.icon} text-ink-4 mb-1`} />
            <div className="font-mono text-lg text-ink-1">{stat.value}</div>
            <div className="font-mono text-[9px] uppercase tracking-wider text-ink-4">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Agent Grid */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {agents.map((agent) => (
          <div key={agent.id} className="rounded-[4px] border border-line bg-bg-1 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <i className={`${agent.icon} text-${agent.color}`} />
                <span className="font-display text-sm text-ink-1">{agent.name}</span>
              </div>
              <span className={`rounded-full border px-2 py-0.5 font-mono text-[9px] uppercase ${
                agent.running ? COLOR_MAP[agent.color] || COLOR_MAP.amber : 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30'
              }`}>
                {agent.running ? 'RUNNING' : 'IDLE'}
              </span>
            </div>
            <p className="font-mono text-[10px] text-ink-4 line-clamp-2">{agent.description}</p>
            
            {/* Metrics */}
            {Object.keys(agent.metrics).length > 0 && (
              <div className="flex flex-wrap gap-2">
                {Object.entries(agent.metrics).map(([key, value]) => (
                  <span key={key} className="font-mono text-[10px] text-ink-3">
                    {key.replace(/_/g, ' ')}: <span className="text-ink-1">{value}</span>
                  </span>
                ))}
              </div>
            )}
            
            {/* Controls */}
            <div className="flex items-center gap-2">
              {agent.running ? (
                <button
                  onClick={() => stopAgent(agent.id)}
                  className="rounded border border-line-strong px-2 py-1 font-mono text-[9px] uppercase text-ink-2 hover:border-red-500 hover:text-red-400 transition-colors"
                >
                  STOP
                </button>
              ) : (
                <button
                  onClick={() => runAgent(agent.id)}
                  disabled={loading || !agent.installed}
                  className="rounded border border-line-strong px-2 py-1 font-mono text-[9px] uppercase text-ink-2 hover:border-amber hover:text-amber transition-colors disabled:opacity-50"
                >
                  {loading ? 'RUNNING...' : 'RUN ONCE'}
                </button>
              )}
              <span className="font-mono text-[9px] text-ink-4">{agent.script}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
