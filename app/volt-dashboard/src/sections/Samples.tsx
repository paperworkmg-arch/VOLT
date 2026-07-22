import { useState, useRef } from 'react'
import { useSamples, useSampleStats } from '@/hooks/use-samples'
import { startScan, analyzeSamples } from '@/lib/api'
import { useQueryClient } from '@tanstack/react-query'

function PlayButton({ sampleId }: { sampleId: number }) {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [playing, setPlaying] = useState(false)

  const toggle = () => {
    if (!audioRef.current) {
      audioRef.current = new Audio(`/api/samples/${sampleId}/stream`)
      audioRef.current.onended = () => setPlaying(false)
      audioRef.current.onerror = () => setPlaying(false)
    }
    if (playing) {
      audioRef.current.pause()
      setPlaying(false)
    } else {
      audioRef.current.play()
      setPlaying(true)
    }
  }

  return (
    <button
      onClick={(e) => { e.stopPropagation(); toggle() }}
      className="w-6 h-6 flex items-center justify-center rounded border border-line-strong hover:border-amber hover:text-amber transition-colors text-ink-3"
      title={playing ? 'Pause' : 'Play'}
    >
      {playing ? (
        <svg width="10" height="10" viewBox="0 0 10 10"><rect x="1" y="1" width="3" height="8" fill="currentColor"/><rect x="6" y="1" width="3" height="8" fill="currentColor"/></svg>
      ) : (
        <svg width="10" height="10" viewBox="0 0 10 10"><polygon points="2,0 10,5 2,10" fill="currentColor"/></svg>
      )}
    </button>
  )
}

function formatDuration(secs: number) {
  if (!secs) return '—'
  const m = Math.floor(secs / 60)
  const s = Math.floor(secs % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

function formatSize(bytes: number) {
  if (!bytes) return '—'
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)}KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`
}

export default function SamplesSection() {
  const [filters, setFilters] = useState<Record<string, string>>({})
  const { data: samples } = useSamples(filters)
  const { data: stats } = useSampleStats()
  const [scanning, setScanning] = useState(false)
  const qc = useQueryClient()

  const handleScan = async () => {
    setScanning(true)
    try { await startScan() } catch {}
    setTimeout(() => { qc.invalidateQueries({ queryKey: ['samples'] }); setScanning(false) }, 3000)
  }
  const handleAnalyze = async () => {
    await analyzeSamples()
    qc.invalidateQueries({ queryKey: ['samples'] })
  }

  const handleDragStart = (e: React.DragEvent, sample: any) => {
    e.dataTransfer.setData('text/uri-list', window.location.origin + `/api/samples/${sample.id}/stream`)
    e.dataTransfer.setData('text/plain', sample.filename)
    e.dataTransfer.effectAllowed = 'copy'
  }

  return (
    <section id="samples" className="space-y-4">
      <h2 className="font-display text-sm uppercase tracking-[0.12em] text-ink-1">SAMPLES</h2>

      {stats && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { label: 'TOTAL', value: stats.total },
            { label: 'KEYS', value: Object.keys(stats.by_key || {}).length },
            { label: 'TYPES', value: Object.keys(stats.by_type || {}).length },
            { label: 'DIRS', value: Object.keys(stats.by_directory || {}).length },
          ].map((s) => (
            <div key={s.label} className="rounded border border-line bg-bg-1 px-3 py-2 text-center">
              <div className="font-mono text-lg text-amber tabular-nums">{s.value}</div>
              <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-ink-4">{s.label}</div>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-2">
        <input
          value={filters.q || ''}
          onChange={(e) => setFilters((f) => ({ ...f, q: e.target.value }))}
          placeholder="Search samples..."
          className="flex-1 rounded border border-line-strong bg-bg-1 px-3 py-2 font-mono text-xs text-ink-2 placeholder:text-ink-5 focus:border-amber focus:outline-none"
        />
        <select
          value={filters.key || ''}
          onChange={(e) => setFilters((f) => ({ ...f, key: e.target.value }))}
          className="rounded border border-line-strong bg-bg-1 px-3 py-2 font-mono text-[10px] text-ink-2 focus:border-amber focus:outline-none"
        >
          <option value="">ALL KEYS</option>
          {['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'].map(k => (
            <option key={k} value={k}>{k}</option>
          ))}
        </select>
        <select
          value={filters.type || ''}
          onChange={(e) => setFilters((f) => ({ ...f, type: e.target.value }))}
          className="rounded border border-line-strong bg-bg-1 px-3 py-2 font-mono text-[10px] text-ink-2 focus:border-amber focus:outline-none"
        >
          <option value="">ALL TYPES</option>
          {['loop','one-shot','project-sample','full-track','export'].map(t => (
            <option key={t} value={t}>{t.toUpperCase()}</option>
          ))}
        </select>
        <button onClick={handleScan} disabled={scanning} className="rounded border border-line-strong px-3 py-2 font-mono text-[10px] uppercase text-ink-2 hover:border-amber hover:text-amber transition-colors disabled:opacity-40">
          {scanning ? 'Scanning...' : 'Scan'}
        </button>
        <button onClick={handleAnalyze} className="rounded border border-line-strong px-3 py-2 font-mono text-[10px] uppercase text-ink-2 hover:border-amber hover:text-amber transition-colors">
          Analyze
        </button>
      </div>

      <p className="font-mono text-[9px] text-ink-5">Drag any row to your DAW to import. Click play to preview.</p>

      <div className="overflow-x-auto rounded-[4px] border border-line max-h-[400px] overflow-y-auto">
        <table className="w-full text-left">
          <thead className="sticky top-0 bg-bg-1">
            <tr className="border-b border-line">
              <th className="px-3 py-2 font-mono text-[9px] uppercase tracking-[0.14em] text-ink-4 w-8"></th>
              <th className="px-3 py-2 font-mono text-[9px] uppercase tracking-[0.14em] text-ink-4">Filename</th>
              <th className="px-3 py-2 font-mono text-[9px] uppercase tracking-[0.14em] text-ink-4">Key</th>
              <th className="px-3 py-2 font-mono text-[9px] uppercase tracking-[0.14em] text-ink-4">Tempo</th>
              <th className="px-3 py-2 font-mono text-[9px] uppercase tracking-[0.14em] text-ink-4">Duration</th>
              <th className="px-3 py-2 font-mono text-[9px] uppercase tracking-[0.14em] text-ink-4">Size</th>
              <th className="px-3 py-2 font-mono text-[9px] uppercase tracking-[0.14em] text-ink-4">Type</th>
            </tr>
          </thead>
          <tbody>
            {samples?.slice(0, 100).map((s) => (
              <tr
                key={s.id}
                draggable
                onDragStart={(e) => handleDragStart(e, s)}
                className="border-b border-line last:border-0 hover:bg-bg-1/50 transition-colors cursor-grab active:cursor-grabbing"
                title={`${s.filename} — drag to DAW`}
              >
                <td className="px-3 py-2"><PlayButton sampleId={s.id} /></td>
                <td className="px-3 py-2 font-mono text-[10px] text-ink-2 truncate max-w-[200px]">{s.filename}</td>
                <td className="px-3 py-2 font-mono text-[10px] text-amber font-semibold">{s.key || '—'}</td>
                <td className="px-3 py-2 font-mono text-[10px] text-ink-3">{s.tempo ? `${s.tempo}` : '—'}</td>
                <td className="px-3 py-2 font-mono text-[10px] text-ink-4">{formatDuration(s.duration)}</td>
                <td className="px-3 py-2 font-mono text-[10px] text-ink-4">{formatSize(s.size_bytes)}</td>
                <td className="px-3 py-2 font-mono text-[10px] text-ink-4">{s.sample_type}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
