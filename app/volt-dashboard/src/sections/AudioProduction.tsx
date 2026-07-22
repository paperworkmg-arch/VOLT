import { useAudioApps } from '@/hooks/use-audio-apps'

const STATUS_COLORS: Record<string, string> = {
  running: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  stopped: 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30',
  error: 'bg-red-500/20 text-red-400 border-red-500/30',
}

export default function AudioProduction() {
  const { apps, loading, launchApp, stopApp } = useAudioApps()

  return (
    <section id="audio-production" className="space-y-4">
      <h2 className="font-display text-sm uppercase tracking-[0.12em] text-ink-1">AUDIO PRODUCTION</h2>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {apps.map((app) => (
          <div key={app.id} className="rounded-[4px] border border-line bg-bg-1 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <i className={`${app.icon} text-amber`} />
                <span className="font-display text-sm text-ink-1">{app.name}</span>
              </div>
              <span className={`rounded-full border px-2 py-0.5 font-mono text-[9px] uppercase ${STATUS_COLORS[app.status] || STATUS_COLORS.stopped}`}>
                {app.status}
              </span>
            </div>
            <p className="font-mono text-[10px] text-ink-4">{app.description}</p>
            {app.port && (
              <p className="font-mono text-[10px] text-ink-3">Port: {app.port}</p>
            )}
            <div className="flex items-center gap-2">
              {app.status === 'running' ? (
                <>
                  {app.url && (
                    <a
                      href={app.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="rounded border border-amber px-2 py-1 font-mono text-[9px] uppercase text-amber hover:bg-amber/10 transition-colors"
                    >
                      OPEN
                    </a>
                  )}
                  <button
                    onClick={() => stopApp(app.id)}
                    className="rounded border border-line-strong px-2 py-1 font-mono text-[9px] uppercase text-ink-2 hover:border-red-500 hover:text-red-400 transition-colors"
                  >
                    STOP
                  </button>
                </>
              ) : (
                <button
                  onClick={() => launchApp(app.id)}
                  disabled={loading}
                  className="rounded border border-line-strong px-2 py-1 font-mono text-[9px] uppercase text-ink-2 hover:border-amber hover:text-amber transition-colors disabled:opacity-50"
                >
                  {loading ? 'LAUNCHING...' : 'LAUNCH'}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
