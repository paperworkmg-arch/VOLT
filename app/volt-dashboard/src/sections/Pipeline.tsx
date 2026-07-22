import { useRef } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { useGSAP } from '@gsap/react'
import ChartTip from '@/components/ChartTip'
import CountUp from '@/components/CountUp'
import Panel from '@/components/Panel'
import SectionHeader from '@/components/SectionHeader'
import {
  PIPELINE_FOOTNOTE,
  PIPELINE_STAGES,
  PIPELINE_VALUE,
  PIPELINE_VALUE_SUB,
} from '@/lib/pipeline'
import { prefersReducedMotion } from '@/lib/motion'

gsap.registerPlugin(ScrollTrigger, useGSAP)

/** §6 — deal-flow pipeline strip with traveling signal pulse. */
export default function Pipeline() {
  const root = useRef<HTMLDivElement>(null)

  useGSAP(
    () => {
      const el = root.current
      if (!el) return
      if (prefersReducedMotion()) return
      const track = el.querySelector<HTMLDivElement>('.pipe-track')
      const nodes = el.querySelectorAll<HTMLDivElement>('.pipe-node')
      const convs = el.querySelectorAll<HTMLSpanElement>('.pipe-conv')
      const pulse = el.querySelector<HTMLDivElement>('.pipe-pulse')
      if (track) gsap.set(track, { scaleX: 0, transformOrigin: '0% 50%' })
      gsap.set(nodes, { scale: 0, opacity: 0 })
      gsap.set(convs, { opacity: 0 })
      const tl = gsap.timeline({ paused: true })
      if (track) tl.to(track, { scaleX: 1, duration: 0.7, ease: 'expo.out' }, 0)
      tl.to(nodes, { scale: 1, opacity: 1, duration: 0.5, ease: 'back.out(2)', stagger: 0.12 }, 0.2).to(
        convs,
        { opacity: 1, duration: 0.3, stagger: 0.1 },
        0.8,
      )
      const st = ScrollTrigger.create({ trigger: el, start: 'top 80%', once: true, onEnter: () => tl.play() })

      /* signal pulse — 24px amber dot traveling the track every 3.2s */
      let pulseTl: gsap.core.Timeline | null = null
      let io: IntersectionObserver | null = null
      if (pulse) {
        pulseTl = gsap
          .timeline({ repeat: -1, paused: true, delay: 1.4 })
          .fromTo(pulse, { left: '0%', opacity: 0 }, { opacity: 1, duration: 0.4, ease: 'power1.out' }, 0)
          .to(pulse, { left: '100%', duration: 3.2, ease: 'power1.inOut' }, 0)
          .to(pulse, { opacity: 0, duration: 0.4, ease: 'power1.in' }, 2.8)
        io = new IntersectionObserver(
          (entries) => {
            if (entries[0].isIntersecting) pulseTl?.play()
            else pulseTl?.pause()
          },
          { threshold: 0.2 },
        )
        io.observe(el)
      }
      return () => {
        st.kill()
        tl.kill()
        pulseTl?.kill()
        io?.disconnect()
      }
    },
    { scope: root },
  )

  return (
    <section id="pipeline" aria-label="Deal flow pipeline" className="scroll-mt-20">
      <SectionHeader
        overline="05 / DEAL FLOW"
        title="ENTERPRISE PIPELINE"
        descriptor="Outreach signal chain mirrored from the Volt Records enterprise console."
      />
      <div ref={root}>
        <Panel meta={PIPELINE_FOOTNOTE} contentClassName="!pt-2">
          <div className="flex flex-col gap-8 lg:flex-row lg:items-stretch">
            {/* stage track */}
            <div className="relative flex-1">
              {/* desktop track */}
              <div
                aria-hidden
                className="pipe-track absolute left-[12.5%] right-[12.5%] top-[27px] hidden h-[2px] bg-line-strong md:block"
              />
              {/* chevron notches */}
              <div aria-hidden className="absolute left-[25%] top-[24px] hidden -translate-x-1/2 font-mono text-[10px] text-line-strong md:block">›</div>
              <div aria-hidden className="absolute left-1/2 top-[24px] hidden -translate-x-1/2 font-mono text-[10px] text-line-strong md:block">›</div>
              <div aria-hidden className="absolute left-[75%] top-[24px] hidden -translate-x-1/2 font-mono text-[10px] text-line-strong md:block">›</div>
              {/* conversion labels on track midpoints */}
              {PIPELINE_STAGES.slice(0, 3).map((s, i) => (
                <span
                  key={s.id}
                  className="pipe-conv absolute top-[20px] hidden -translate-x-1/2 bg-bg-1 px-1.5 font-mono text-[9px] uppercase tracking-[0.1em] text-ink-3 md:block"
                  style={{ left: `${25 + i * 25}%` }}
                >
                  {s.edgeToNext}
                </span>
              ))}
              {/* traveling pulse */}
              <div
                aria-hidden
                className="pipe-pulse absolute top-[27px] hidden h-[24px] w-[24px] -translate-x-1/2 -translate-y-1/2 rounded-full opacity-0 md:block"
                style={{
                  background: 'radial-gradient(circle, rgba(232,163,61,0.9) 0%, rgba(232,163,61,0.25) 45%, transparent 70%)',
                }}
              />
              {/* nodes */}
              <div className="grid grid-cols-2 gap-y-10 md:grid-cols-4">
                {PIPELINE_STAGES.map((stage, i) => {
                  const last = i === PIPELINE_STAGES.length - 1
                  return (
                    <ChartTip key={stage.id} label={stage.tooltip}>
                      <div className="group flex cursor-default flex-col items-center text-center">
                        <span className="label-micro">{stage.label}</span>
                        <div className="pipe-node relative my-3 flex h-[10px] items-center">
                          <span
                            aria-hidden
                            className={
                              last
                                ? 'block h-2.5 w-2.5 rounded-full bg-amber ring-2 ring-vermilion motion-safe:animate-ring-pulse'
                                : 'block h-2.5 w-2.5 rounded-full bg-amber shadow-glow'
                            }
                          />
                        </div>
                        <span
                          className={`font-mono text-[34px] font-bold leading-none transition-colors duration-150 group-hover:text-amber-hi ${last ? 'text-amber' : 'text-ink-1'}`}
                          style={{ fontVariantNumeric: 'tabular-nums' }}
                        >
                          <CountUp value={stage.value} duration={1} delay={0.2 + i * 0.12} format={(v) => Math.round(v).toLocaleString('en-US')} />
                        </span>
                        <span className="mt-1.5 font-mono text-[9px] uppercase tracking-[0.12em] text-ink-4">{stage.sub}</span>
                      </div>
                    </ChartTip>
                  )
                })}
              </div>
            </div>
            {/* pipeline value */}
            <div className="flex flex-col items-center justify-center border-t border-line pt-6 lg:border-l lg:border-t-0 lg:pl-8 lg:pt-0">
              <span className="label-micro">PIPELINE VALUE</span>
              <span className="mt-2 font-mono text-[22px] font-bold text-amber" style={{ fontVariantNumeric: 'tabular-nums' }}>
                {PIPELINE_VALUE}
              </span>
              <span className="mt-1 font-mono text-[9px] uppercase tracking-[0.12em] text-ink-4">{PIPELINE_VALUE_SUB}</span>
            </div>
          </div>
        </Panel>
      </div>
    </section>
  )
}
