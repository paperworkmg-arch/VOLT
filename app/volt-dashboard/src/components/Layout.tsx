import { useEffect } from 'react'
import type { ReactNode } from 'react'
import Lenis from 'lenis'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import Footer from '@/components/Footer'
import Navbar from '@/components/Navbar'
import { prefersReducedMotion, setLenis } from '@/lib/motion'

interface LayoutProps {
  children: ReactNode
}

/** App shell — sticky console top bar, Lenis smooth scroll, global grain, footer. */
export default function Layout({ children }: LayoutProps) {
  useEffect(() => {
    if (prefersReducedMotion()) return
    const lenis = new Lenis({ lerp: 0.09, wheelMultiplier: 0.9 })
    setLenis(lenis)
    const onScroll = () => ScrollTrigger.update()
    lenis.on('scroll', onScroll)
    let raf = 0
    const loop = (time: number) => {
      lenis.raf(time)
      raf = requestAnimationFrame(loop)
    }
    raf = requestAnimationFrame(loop)
    return () => {
      cancelAnimationFrame(raf)
      lenis.destroy()
      setLenis(null)
    }
  }, [])

  return (
    <div className="min-h-[100dvh] bg-bg-0">
      {/* global grain — fixed full-viewport, 5% opacity, blend overlay */}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 z-[90] opacity-[0.05] mix-blend-overlay"
        style={{ backgroundImage: 'url(/texture-noise.png)', backgroundRepeat: 'repeat' }}
      />
      <Navbar />
      <main>{children}</main>
      <Footer />
    </div>
  )
}
