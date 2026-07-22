import { useTasks } from '@/hooks/use-tasks'
import { toggleTask, runTask } from '@/lib/api'
import { useQueryClient } from '@tanstack/react-query'

const STATUS_DOT: Record<string, string> = {
  pending: 'bg-zinc-400', running: 'bg-amber motion-safe:animate-pulse', completed: 'bg-emerald-500', failed: 'bg-red-500',
}

export default function TasksSection() {
  const { data: tasks } = useTasks()
  const qc = useQueryClient()

  const handleToggle = async (id: number) => {
    await toggleTask(id)
    qc.invalidateQueries({ queryKey: ['tasks'] })
  }
  const handleRun = async (id: number) => {
    await runTask(id)
    qc.invalidateQueries({ queryKey: ['tasks'] })
  }

  return (
    <section id="tasks" className="space-y-4">
      <h2 className="font-display text-sm uppercase tracking-[0.12em] text-ink-1">TASKS</h2>
      <div className="overflow-x-auto rounded-[4px] border border-line">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-line bg-bg-1">
              <th className="px-3 py-2 font-mono text-[9px] uppercase tracking-[0.14em] text-ink-4">Name</th>
              <th className="px-3 py-2 font-mono text-[9px] uppercase tracking-[0.14em] text-ink-4">Status</th>
              <th className="px-3 py-2 font-mono text-[9px] uppercase tracking-[0.14em] text-ink-4">Schedule</th>
              <th className="px-3 py-2 font-mono text-[9px] uppercase tracking-[0.14em] text-ink-4">Agent</th>
              <th className="px-3 py-2 font-mono text-[9px] uppercase tracking-[0.14em] text-ink-4">Actions</th>
            </tr>
          </thead>
          <tbody>
            {tasks?.map((t) => (
              <tr key={t.id} className="border-b border-line last:border-0 hover:bg-bg-1/50 transition-colors">
                <td className="px-3 py-2 font-mono text-xs text-ink-2">{t.name}</td>
                <td className="px-3 py-2">
                  <span className="flex items-center gap-1.5">
                    <span className={`h-1.5 w-1.5 rounded-full ${STATUS_DOT[t.status] || 'bg-zinc-500'}`} />
                    <span className="font-mono text-[10px] uppercase text-ink-3">{t.status}</span>
                  </span>
                </td>
                <td className="px-3 py-2 font-mono text-[10px] text-ink-4">{t.scheduled_cron || '—'}</td>
                <td className="px-3 py-2 font-mono text-[10px] text-ink-4">{t.agent || '—'}</td>
                <td className="px-3 py-2 flex gap-1.5">
                  <button onClick={() => handleRun(t.id)} className="rounded border border-line-strong px-2 py-0.5 font-mono text-[9px] uppercase text-ink-2 hover:border-amber hover:text-amber transition-colors">Run</button>
                  <button onClick={() => handleToggle(t.id)} className="rounded border border-line-strong px-2 py-0.5 font-mono text-[9px] uppercase text-ink-2 hover:border-amber hover:text-amber transition-colors">
                    {t.enabled ? 'Disable' : 'Enable'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
