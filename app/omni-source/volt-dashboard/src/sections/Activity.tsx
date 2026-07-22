import { useActivity } from '@/hooks/use-activity'

const LEVEL_COLOR: Record<string, string> = {
  info: 'text-amber', error: 'text-vermilion', warning: 'text-orange-400',
}
const SOURCE_BADGE: Record<string, string> = {
  system: 'border-emerald-500/30 text-emerald-400', scheduler: 'border-amber/30 text-amber',
  swarm: 'border-purple-400/30 text-purple-400', agents: 'border-cyan-400/30 text-cyan-400',
  scanner: 'border-blue-400/30 text-blue-400', notification: 'border-amber/30 text-amber',
  contacts: 'border-pink-400/30 text-pink-400', cleaner: 'border-lime-400/30 text-lime-400',
}

export default function ActivitySection() {
  const { data: activity, isLoading } = useActivity()

  return (
    <section id="activity" className="space-y-4">
      <h2 className="font-display text-sm uppercase tracking-[0.12em] text-ink-1">ACTIVITY</h2>
      <div className="space-y-1 max-h-[400px] overflow-y-auto pr-1 scrollbar-thin">
        {isLoading && <p className="font-mono text-[10px] text-ink-4">Loading...</p>}
        {activity?.map((a) => (
          <div key={a.id} className="flex items-start gap-2 rounded px-2 py-1.5 hover:bg-bg-1/50 transition-colors">
            <span className="mt-0.5 shrink-0 font-mono text-[9px] text-ink-5 tabular-nums">
              {a.created_at?.slice(11, 19)}
            </span>
            <span className={`shrink-0 rounded border px-1.5 py-0.5 font-mono text-[8px] uppercase ${SOURCE_BADGE[a.source] || 'border-line text-ink-4'}`}>
              {a.source}
            </span>
            <span className={`font-mono text-[10px] ${LEVEL_COLOR[a.level] || 'text-ink-3'}`}>
              {a.message}
            </span>
          </div>
        ))}
      </div>
    </section>
  )
}
