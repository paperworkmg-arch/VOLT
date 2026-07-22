import type { Bucket } from '@/lib/catalog'
import { BUCKET_COLORS } from '@/lib/catalog'
import { cn } from '@/lib/utils'

interface VerdictBadgeProps {
  bucket: Bucket
  className?: string
}

/** Engraved toggle-style verdict badge (design.md §8.5). */
export default function VerdictBadge({ bucket, className }: VerdictBadgeProps) {
  const color = BUCKET_COLORS[bucket]
  return (
    <span
      className={cn(
        'inline-block whitespace-nowrap rounded-[2px] px-1.5 py-0.5 font-mono text-[10px] font-bold uppercase tracking-[0.1em]',
        className,
      )}
      style={{
        color,
        border: `1px solid ${color}80`,
        backgroundColor: `${color}14`,
      }}
    >
      {bucket}
    </span>
  )
}
