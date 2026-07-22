import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import VuMeter from '@/components/VuMeter'
import { EASE_OUT_EXPO, scrollToTarget } from '@/lib/motion'
import { cn } from '@/lib/utils'

const SECTIONS = [
  { id: 'metrics', label: 'METRICS' },
  { id: 'analyzers', label: 'ANALYZERS' },
  { id: 'prospects', label: 'PROSPECTS' },
  { id: 'ledger', label: 'LEDGER' },
  { id: 'leads', label: 'LEADS' },
  { id: 'agents', label: 'AGENTS' },
  { id: 'tasks', label: 'TASKS' },
  { id: 'swarm', label: 'SWARM' },
  { id: 'samples', label: 'SAMPLES' },
  { id: 'vault', label: 'VAULT' },
  { id: 'activity', label: 'ACTIVITY' },
  { id: 'system', label: 'SYSTEM' },
  { id: 'pipeline', label: 'PIPELINE' },
] as const

function useSessionClock() {
  const [now, setNow] = useState<string>('--:--:--')
  useEffect(() => {
    let iv: ReturnType<typeof setInterval> | null = null
    const tick = () => {
      const d = new Date()
      setNow(
        [d.getHours(), d.getMinutes(), d.getSeconds()]
          .map((n) => String(n).padStart(2, '0'))
          .join(':'),
      )
    }
    /* ambient loops start after 800ms (home.md §0) */
    const t = setTimeout(() => {
      tick()
      iv = setInterval(tick, 1000)
    }, 800)
    const onVis = () => {
      if (document.hidden && iv) {
        clearInterval(iv)
        iv = null
      } else if (!document.hidden && !iv) {
        tick()
        iv = setInterval(tick, 1000)
      }
    }
    document.addEventListener('visibilitychange', onVis)
    return () => {
      clearTimeout(t)
      if (iv) clearInterval(iv)
      document.removeEventListener('visibilitychange', onVis)
    }
  }, [])
  return now
}

function useScrollSpy() {
  const [active, setActive] = useState<string>('')
  useEffect(() => {
    const obs = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) setActive(e.target.id)
        }
      },
      { rootMargin: '-30% 0px -60% 0px', threshold: 0 },
    )
    SECTIONS.forEach(({ id }) => {
      const el = document.getElementById(id)
      if (el) obs.observe(el)
    })
    return () => obs.disconnect()
  }, [])
  return active
}

/** ConsoleTopBar — sticky rack rail with VU meters, clock, REC and scroll-spy anchors. */
export default function Navbar() {
  const clock = useSessionClock()
  const active = useScrollSpy()
  const [drawerOpen, setDrawerOpen] = useState(false)

  const go = (id: string) => {
    setDrawerOpen(false)
    scrollToTarget(`#${id}`, -64)
  }

  return (
    <motion.header
      className="sticky top-0 z-50 h-14 border-b border-line bg-bg-0/90 backdrop-blur-[8px]"
      initial={{ y: -56 }}
      animate={{ y: 0 }}
      transition={{ duration: 0.5, ease: EASE_OUT_EXPO }}
    >
      <motion.div
        className="mx-auto flex h-full max-w-console items-center justify-between gap-4 px-5 md:px-8"
        initial="hidden"
        animate="show"
        transition={{ staggerChildren: 0.06, delayChildren: 0.15 }}
      >
        {/* left — wordmark */}
        <motion.div
          className="flex items-center gap-2.5"
          variants={{ hidden: { opacity: 0, y: -8 }, show: { opacity: 1, y: 0 } }}
          transition={{ duration: 0.4, ease: EASE_OUT_EXPO }}
        >
          <img src="/logo-volt.svg" alt="Volt Records bolt badge" className="h-5 w-5" />
          <span className="font-display text-[13px] uppercase tracking-[0.08em] text-ink-1">
            VOLT RECORDS
          </span>
          <span aria-hidden className="mx-1 hidden h-4 w-px bg-line-strong sm:block" />
          <span className="hidden font-mono text-[10px] uppercase tracking-[0.16em] text-ink-3 sm:block">
            OMNI-STUDIO
          </span>
        </motion.div>

        {/* center — scroll-spy anchors */}
        <motion.nav
          aria-label="Section navigation"
          className="hidden items-center gap-6 lg:flex"
          variants={{ hidden: { opacity: 0 }, show: { opacity: 1 } }}
          transition={{ duration: 0.4 }}
        >
          {SECTIONS.map(({ id, label }) => (
            <button
              key={id}
              type="button"
              onClick={() => go(id)}
              className={cn(
                'relative pb-1 font-mono text-[10px] uppercase tracking-[0.14em] transition-colors duration-150',
                active === id ? 'text-amber' : 'text-ink-3 hover:text-amber',
              )}
            >
              {label}
              <span
                aria-hidden
                className={cn(
                  'absolute -bottom-[3px] left-0 h-[2px] w-full bg-amber transition-opacity duration-150',
                  active === id ? 'opacity-100' : 'opacity-0',
                )}
              />
            </button>
          ))}
        </motion.nav>

        {/* right — VU, clock, REC */}
        <motion.div
          className="flex items-center gap-4"
          variants={{ hidden: { opacity: 0, y: -8 }, show: { opacity: 1, y: 0 } }}
          transition={{ duration: 0.4, ease: EASE_OUT_EXPO }}
        >
          <VuMeter />
          <div className="hidden items-baseline gap-2 sm:flex">
            <span className="font-mono text-[9px] uppercase tracking-[0.14em] text-ink-4">SESSION</span>
            <span className="font-mono text-[11px] text-ink-2" style={{ fontVariantNumeric: 'tabular-nums' }}>
              {clock}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <span
              aria-hidden
              className="h-1.5 w-1.5 rounded-full bg-vermilion motion-safe:animate-rec-breathe"
            />
            <span className="font-mono text-[9px] uppercase tracking-[0.14em] text-ink-3">LIVE</span>
          </div>
          {/* mobile hamburger */}
          <button
            type="button"
            aria-label={drawerOpen ? 'Close navigation' : 'Open navigation'}
            aria-expanded={drawerOpen}
            onClick={() => setDrawerOpen((v) => !v)}
            className="flex h-8 w-8 flex-col items-center justify-center gap-1.5 rounded-[3px] border border-line-strong lg:hidden"
          >
            <span className={cn('h-px w-4 bg-ink-2 transition-transform duration-150', drawerOpen && 'translate-y-[3.5px] rotate-45')} />
            <span className={cn('h-px w-4 bg-ink-2 transition-transform duration-150', drawerOpen && '-translate-y-[3px] -rotate-45')} />
          </button>
        </motion.div>
      </motion.div>

      {/* mobile drawer */}
      <AnimatePresence>
        {drawerOpen && (
          <motion.nav
            aria-label="Mobile section navigation"
            className="absolute left-0 right-0 top-14 border-b border-line bg-bg-1 lg:hidden"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2, ease: EASE_OUT_EXPO }}
          >
            <div className="flex flex-col px-5 py-3">
              {SECTIONS.map(({ id, label }, i) => (
                <motion.button
                  key={id}
                  type="button"
                  onClick={() => go(id)}
                  className={cn(
                    'border-b border-line py-3 text-left font-mono text-[11px] uppercase tracking-[0.14em] last:border-0',
                    active === id ? 'text-amber' : 'text-ink-2',
                  )}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.05 * i, duration: 0.25, ease: EASE_OUT_EXPO }}
                >
                  {label}
                </motion.button>
              ))}
            </div>
          </motion.nav>
        )}
      </AnimatePresence>
    </motion.header>
  )
}
