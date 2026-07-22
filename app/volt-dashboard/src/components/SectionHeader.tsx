import { motion } from 'framer-motion'
import { EASE_OUT_EXPO } from '@/lib/motion'

interface SectionHeaderProps {
  overline: string
  title: string
  descriptor?: string
}

/** Module header: amber overline, display title, right descriptor (design.md §8.3). */
export default function SectionHeader({ overline, title, descriptor }: SectionHeaderProps) {
  return (
    <motion.div
      className="mb-8 flex flex-col gap-3 md:flex-row md:items-end md:justify-between"
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, margin: '0px 0px -20% 0px' }}
      transition={{ staggerChildren: 0.08 }}
    >
      <div className="min-w-0">
        <motion.p
          className="mb-2 font-mono text-[10px] font-medium uppercase tracking-[0.16em] text-amber"
          variants={{ hidden: { opacity: 0, x: -16 }, show: { opacity: 1, x: 0 } }}
          transition={{ duration: 0.5, ease: EASE_OUT_EXPO }}
        >
          {overline}
        </motion.p>
        <motion.h2
          className="font-display uppercase leading-[1.1] text-ink-1"
          style={{ fontSize: 'clamp(20px, 2.4vw, 28px)' }}
          variants={{ hidden: { opacity: 0, y: 24 }, show: { opacity: 1, y: 0 } }}
          transition={{ duration: 0.6, ease: EASE_OUT_EXPO }}
        >
          {title}
        </motion.h2>
      </div>
      {descriptor && (
        <motion.p
          className="max-w-[42ch] text-[13px] leading-relaxed text-ink-3 md:text-right"
          variants={{ hidden: { opacity: 0 }, show: { opacity: 1 } }}
          transition={{ duration: 0.6, ease: EASE_OUT_EXPO }}
        >
          {descriptor}
        </motion.p>
      )}
    </motion.div>
  )
}
