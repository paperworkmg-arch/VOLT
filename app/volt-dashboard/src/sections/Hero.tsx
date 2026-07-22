import { memo, useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import gsap from 'gsap'
import { useGSAP } from '@gsap/react'
import { EASE_OUT_EXPO, prefersReducedMotion } from '@/lib/motion'

gsap.registerPlugin(useGSAP)

const OVERLINE = 'OMNI-STUDIO // CATALOG INTELLIGENCE'

const META: { k: string; v: string; amber?: boolean }[] = [
  { k: 'DATASET', v: 'ANALYSIS_RESULTS.JSON' },
  { k: 'RECORDS', v: '198' },
  { k: 'PRODUCER', v: 'MYKEL T BROOKS' },
  { k: 'ENGINE', v: 'HPI v2' },
  { k: 'STATUS', v: 'ACQUISITION WINDOW OPEN', amber: true },
]

/** Type-on overline with amber block caret (home.md §1). */
function TypeOverline() {
  const [text, setText] = useState('')
  const [caretOn, setCaretOn] = useState(true)
  const [caretDone, setCaretDone] = useState(false)

  useEffect(() => {
    if (prefersReducedMotion()) {
      setText(OVERLINE)
      setCaretDone(true)
      return
    }
    let i = 0
    const iv = setInterval(() => {
      i += 1
      setText(OVERLINE.slice(0, i))
      if (i >= OVERLINE.length) {
        clearInterval(iv)
        /* caret blinks twice then disappears */
        let blinks = 0
        const blink = setInterval(() => {
          blinks += 1
          setCaretOn((v) => !v)
          if (blinks >= 4) {
            clearInterval(blink)
            setCaretDone(true)
          }
        }, 240)
      }
    }, 24)
    return () => clearInterval(iv)
  }, [])

  return (
    <p className="mb-5 font-mono text-[11px] uppercase tracking-[0.2em] text-amber" aria-label={OVERLINE}>
      <span aria-hidden>{text}</span>
      {!caretDone && (
        <span aria-hidden className="ml-1 inline-block h-3 w-2 translate-y-[2px] bg-amber" style={{ opacity: caretOn ? 1 : 0 }} />
      )}
    </p>
  )
}

/** Decorative static VU scale (aria-hidden) with one sweep -24 deg to +3 deg. */
const HeroVuScale = memo(function HeroVuScale() {
  const needle = useRef<SVGGElement>(null)
  useGSAP(() => {
    if (!needle.current) return
    if (prefersReducedMotion()) {
      gsap.set(needle.current, { attr: { transform: 'rotate(3 60 62)' } })
      return
    }
    gsap.fromTo(
      needle.current,
      { attr: { transform: 'rotate(-24 60 62)' } },
      { attr: { transform: 'rotate(3 60 62)' }, duration: 1.4, delay: 0.9, ease: 'elastic.out(1, 0.45)' },
    )
  })

  return (
    <svg width="120" height="64" viewBox="0 0 120 64" aria-hidden="true" className="hidden opacity-80 lg:block">
      {Array.from({ length: 13 }, (_, i) => -30 + i * 5).map((deg) => {
        const rad = ((deg - 90) * Math.PI) / 180
        const long = deg % 15 === 0
        return (
          <line
            key={deg}
            x1={60 + 52 * Math.cos(rad)}
            y1={62 + 52 * Math.sin(rad)}
            x2={60 + (long ? 44 : 47) * Math.cos(rad)}
            y2={62 + (long ? 44 : 47) * Math.sin(rad)}
            stroke={deg >= 3 ? '#D95B33' : '#3D332A'}
            strokeWidth="1"
          />
        )
      })}
      <text x="60" y="30" textAnchor="middle" fill="#57493A" fontSize="7" fontFamily="'JetBrains Mono', monospace" letterSpacing="2">
        VU
      </text>
      <g ref={needle} transform="rotate(-24 60 62)">
        <line x1="60" y1="62" x2="60" y2="18" stroke="#B3A58D" strokeWidth="1.2" />
        <line x1="60" y1="24" x2="60" y2="18" stroke="#E8A33D" strokeWidth="2" />
      </g>
      <circle cx="60" cy="62" r="2" fill="#3D332A" />
    </svg>
  )
})

export default function Hero() {
  const reduced = prefersReducedMotion()
  return (
    <section id="top" aria-label="Console hero" className="relative overflow-hidden">
      <motion.div
        className="absolute inset-0"
        initial={reduced ? false : { scale: 1.06 }}
        animate={{ scale: 1 }}
        transition={{ duration: 1.6, ease: EASE_OUT_EXPO }}
      >
        <img
          src="/console-hero.png"
          alt=""
          aria-hidden
          className="h-full w-full object-cover object-center"
        />
      </motion.div>
      <motion.div
        className="absolute inset-0 bg-bg-0/[0.82]"
        initial={reduced ? false : { opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4 }}
      />
      <div aria-hidden className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-b from-transparent to-bg-0" />

      <div className="relative mx-auto flex min-h-[52vh] max-w-console flex-col justify-center px-5 pb-24 pt-20 md:px-8">
        <div className="grid grid-cols-12 items-end gap-4">
          <div className="col-span-12 lg:col-span-9">
            <TypeOverline />
            <h1
              className="font-display uppercase leading-[0.95] tracking-[-0.01em] text-ink-1"
              style={{ fontSize: 'clamp(44px, 7vw, 96px)' }}
            >
              <span className="block overflow-hidden">
                <motion.span
                  className="block"
                  initial={reduced ? false : { y: 64, skewY: 3, opacity: 0 }}
                  animate={{ y: 0, skewY: 0, opacity: 1 }}
                  transition={{ duration: 0.7, ease: EASE_OUT_EXPO, delay: 0.25 }}
                >
                  THE CATALOG,
                </motion.span>
              </span>
              <span className="block overflow-hidden">
                <motion.span
                  className="block text-amber"
                  initial={reduced ? false : { y: 64, skewY: 3, opacity: 0 }}
                  animate={{ y: 0, skewY: 0, opacity: 1 }}
                  transition={{ duration: 0.7, ease: EASE_OUT_EXPO, delay: 0.37 }}
                >
                  METERED.
                </motion.span>
              </span>
            </h1>
            <motion.p
              className="mt-6 max-w-[56ch] text-[15px] leading-[1.6] text-ink-2"
              initial={reduced ? false : { opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, ease: EASE_OUT_EXPO, delay: 0.5 }}
            >
              198 analyzed recordings from the Volt Records vault — tempo, key, tonal brightness,
              energy density, structural velocity, market modularity and the Hit Potential Index,
              compiled into one A&amp;R control surface.
            </motion.p>
          </div>
          <div className="col-span-3 hidden justify-end lg:flex">
            <HeroVuScale />
          </div>
        </div>

        <motion.div
          className="absolute inset-x-5 bottom-8 flex flex-wrap items-center gap-x-0 gap-y-2 md:inset-x-8"
          initial="hidden"
          animate="show"
          transition={{ staggerChildren: 0.06, delayChildren: 0.7 }}
        >
          {META.map(({ k, v, amber }, i) => (
            <motion.div
              key={k}
              className="flex items-center"
              variants={{ hidden: { opacity: 0, y: 8 }, show: { opacity: 1, y: 0 } }}
              transition={{ duration: 0.4, ease: EASE_OUT_EXPO }}
            >
              {i > 0 && <span aria-hidden className="mx-3 h-3 w-px bg-line-strong" />}
              <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-3">
                {k} —{' '}
                <span className={amber ? 'text-amber' : 'text-ink-2'}>{v}</span>
              </span>
              {amber && (
                <span aria-hidden className="ml-2 h-1.5 w-1.5 rounded-full bg-amber motion-safe:animate-rec-breathe" />
              )}
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  )
}
