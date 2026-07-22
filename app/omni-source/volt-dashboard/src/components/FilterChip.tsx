import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface FilterChipProps {
  active?: boolean
  onClick?: () => void
  children: ReactNode
  count?: number
  clearable?: boolean
  ariaLabel?: string
}

/** Mono filter chip with 120ms state change (design.md §8.6). */
export default function FilterChip({ active, onClick, children, count, clearable, ariaLabel }: FilterChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      aria-label={ariaLabel}
      className={cn(
        'inline-flex h-7 items-center gap-1.5 rounded-[2px] border px-2 font-mono text-[10px] uppercase tracking-[0.1em] transition-colors duration-150',
        active
          ? 'border-amber bg-amber text-bg-0'
          : 'border-line-strong text-ink-2 hover:border-[#E8A33D66] hover:text-amber',
      )}
    >
      <span>{children}</span>
      {typeof count === 'number' && (
        <span className={active ? 'text-bg-0/70' : 'text-ink-4'}>{count}</span>
      )}
      {active && clearable && <span aria-hidden className="ml-0.5">×</span>}
    </button>
  )
}
