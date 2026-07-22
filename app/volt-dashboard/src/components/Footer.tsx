import { motion } from 'framer-motion'
import { StaticVuGlyph } from '@/components/VuMeter'
import { TOTAL_TRACKS } from '@/lib/catalog'

/** Console footer (design.md §8.10, home.md §7). */
export default function Footer() {
  return (
    <motion.footer
      className="mt-24 border-t border-line bg-bg-0"
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true, margin: '0px 0px -10% 0px' }}
      transition={{ duration: 0.6 }}
    >
      {/* centered bolt glyph above the footer row */}
      <div className="flex justify-center py-6">
        <img src="/logo-volt.svg" alt="" aria-hidden className="h-4 w-4 opacity-60" />
      </div>
      <div className="mx-auto flex max-w-console flex-col items-center gap-3 border-t border-line px-5 py-6 text-center md:flex-row md:justify-between md:text-left md:px-8">
        <div className="flex items-center gap-2">
          <img src="/logo-volt.svg" alt="" aria-hidden className="h-4 w-4" />
          <span className="font-display text-[11px] uppercase tracking-[0.08em] text-ink-1">
            VOLT RECORDS © 2025
          </span>
        </div>
        <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-3">
          OMNI-STUDIO · CATALOG INTELLIGENCE v2.4 · {TOTAL_TRACKS} RECORDS BUNDLED · NO EXTERNAL CALLS
        </p>
        <div className="flex items-center gap-2">
          <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-2">
            PRODUCER — MYKEL T BROOKS
          </span>
          <StaticVuGlyph />
        </div>
      </div>
    </motion.footer>
  )
}
