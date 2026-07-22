import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface PanelProps {
  title?: string
  meta?: ReactNode
  children: ReactNode
  className?: string
  contentClassName?: string
  id?: string
  ariaLabel?: string
}

/** Rack-unit panel: 1px hairline frame, 4px radius, corner screws, title rail. */
export default function Panel({ title, meta, children, className, contentClassName, id, ariaLabel }: PanelProps) {
  return (
    <section id={id} aria-label={ariaLabel} className={cn('console-panel panel-scanline', className)}>
      {/* corner screws — 2px dots, 8px from each corner */}
      <span aria-hidden className="pointer-events-none absolute left-2 top-2 h-0.5 w-0.5 rounded-full bg-line-strong" />
      <span aria-hidden className="pointer-events-none absolute right-2 top-2 h-0.5 w-0.5 rounded-full bg-line-strong" />
      <span aria-hidden className="pointer-events-none absolute bottom-2 left-2 h-0.5 w-0.5 rounded-full bg-line-strong" />
      <span aria-hidden className="pointer-events-none absolute bottom-2 right-2 h-0.5 w-0.5 rounded-full bg-line-strong" />
      {(title || meta) && (
        <header className="mb-4 flex items-baseline justify-between gap-4 border-b border-line px-4 pb-3 pt-4 md:px-6">
          <h3 className="label-micro">{title}</h3>
          {meta && <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-3">{meta}</div>}
        </header>
      )}
      <div className={cn('px-4 pb-4 md:px-6 md:pb-6', contentClassName)}>{children}</div>
    </section>
  )
}
