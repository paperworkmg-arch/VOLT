import type { ReactNode } from 'react'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'

/** Console-styled tooltip wrapper (design.md §8.8). */
export default function ChartTip({ label, children }: { label: ReactNode; children: ReactNode }) {
  return (
    <TooltipProvider delayDuration={80}>
      <Tooltip>
        <TooltipTrigger asChild>{children}</TooltipTrigger>
        <TooltipContent
          sideOffset={6}
          className="rounded-[3px] border border-line-strong bg-bg-2 px-2 py-1 font-mono text-[11px] text-ink-1 shadow-panel"
        >
          {label}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
