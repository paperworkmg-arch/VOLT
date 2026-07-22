import { useSystemHealth, useCleanerStatus, useNotifications } from '@/hooks/use-system'
import { runCleaner } from '@/lib/api'
import { useQueryClient } from '@tanstack/react-query'

export default function SystemSection() {
  const { data: health } = useSystemHealth()
  const { data: cleaner } = useCleanerStatus()
  const { data: notifications } = useNotifications()
  const qc = useQueryClient()

  const handleClean = async () => {
    await runCleaner()
    qc.invalidateQueries({ queryKey: ['cleaner'] })
    qc.invalidateQueries({ queryKey: ['system-health'] })
  }

  const diskPercent = cleaner?.percent ?? health?.disk?.percent ?? 0

  return (
    <section id="system" className="space-y-4">
      <h2 className="font-display text-sm uppercase tracking-[0.12em] text-ink-1">SYSTEM</h2>

      {/* Disk gauge */}
      <div className="flex items-center gap-6">
        <div className="relative h-24 w-24 shrink-0">
          <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90">
            <circle cx="50" cy="50" r="40" fill="none" stroke="var(--line)" strokeWidth="8" />
            <circle cx="50" cy="50" r="40" fill="none" stroke="var(--amber)" strokeWidth="8"
              strokeDasharray={`${diskPercent * 2.51} 251`} strokeLinecap="round" />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="font-mono text-sm text-amber tabular-nums">{Math.round(diskPercent)}%</span>
          </div>
        </div>
        <div className="space-y-2 flex-1">
          <div className="flex justify-between">
            <span className="font-mono text-[10px] text-ink-4">DISK USAGE</span>
            <span className="font-mono text-[10px] text-ink-3">{cleaner?.usage_gb ?? health?.disk?.usage_gb ?? '—'} / {cleaner?.limit_gb ?? health?.disk?.limit_gb ?? 700} GB</span>
          </div>
          <button onClick={handleClean} className="rounded border border-vermilion/30 bg-vermilion/10 px-3 py-1.5 font-mono text-[9px] uppercase tracking-[0.1em] text-vermilion hover:bg-vermilion/20 transition-colors">
            Clean Now
          </button>
        </div>
      </div>

      {/* Agent status */}
      {health?.agents && (
        <div className="grid grid-cols-4 gap-2">
          {[
            { label: 'TOTAL', value: health.agents.total, color: 'text-ink-2' },
            { label: 'IDLE', value: health.agents.idle, color: 'text-emerald-400' },
            { label: 'WORKING', value: health.agents.working, color: 'text-amber' },
            { label: 'PAUSED', value: health.agents.paused, color: 'text-zinc-400' },
          ].map((s) => (
            <div key={s.label} className="rounded border border-line bg-bg-1 px-2 py-2 text-center">
              <div className={`font-mono text-sm tabular-nums ${s.color}`}>{s.value}</div>
              <div className="font-mono text-[8px] uppercase tracking-[0.14em] text-ink-5">{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Database sizes */}
      {health?.databases && (
        <div className="space-y-1">
          <span className="font-mono text-[9px] uppercase tracking-[0.14em] text-ink-4">Databases</span>
          {Object.entries(health.databases).map(([name, db]) => (
            <div key={name} className="flex items-center justify-between rounded border border-line px-3 py-1.5">
              <span className="font-mono text-[10px] text-ink-3">{name}</span>
              <span className="font-mono text-[10px] text-ink-4">{db.size_mb} MB</span>
            </div>
          ))}
        </div>
      )}

      {/* Notifications */}
      {notifications && notifications.length > 0 && (
        <div className="space-y-1">
          <span className="font-mono text-[9px] uppercase tracking-[0.14em] text-ink-4">Notifications</span>
          {notifications.slice(0, 5).map((n) => (
            <div key={n.id} className="rounded border border-line bg-bg-1 px-3 py-2">
              <span className="font-mono text-[10px] text-ink-3">{n.message}</span>
              <span className="ml-2 font-mono text-[9px] text-ink-5">{n.created_at?.slice(0, 16)}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
