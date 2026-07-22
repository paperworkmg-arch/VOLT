import Lenis from 'lenis'

/* Shared easing (design.md §7): easeOutExpo-ish reveal */
export const EASE_OUT_EXPO: [number, number, number, number] = [0.22, 1, 0.36, 1]

export function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined') return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/* Module-level Lenis singleton so the Navbar can drive anchor scrolling */
let lenis: Lenis | null = null

export function setLenis(instance: Lenis | null) {
  lenis = instance
}

export function getLenis(): Lenis | null {
  return lenis
}

export function scrollToTarget(selector: string, offset = -64) {
  const el = document.querySelector(selector)
  if (!el) return
  const l = getLenis()
  if (l) {
    l.scrollTo(el as HTMLElement, { offset, duration: 1.2 })
  } else {
    el.scrollIntoView({ behavior: prefersReducedMotion() ? 'auto' : 'smooth', block: 'start' })
  }
}
