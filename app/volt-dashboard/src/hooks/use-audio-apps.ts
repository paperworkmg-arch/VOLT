import { useState, useEffect } from 'react'

interface AudioApp {
  id: string
  name: string
  description: string
  status: 'running' | 'stopped' | 'error'
  port?: number
  url?: string
  icon: string
}

const MOCK_AUDIO_APPS: AudioApp[] = [
  {
    id: 'stabledaw',
    name: 'StableDAW',
    description: 'AI Audio DAW with text-to-audio, inpainting, and LoRA training',
    status: 'stopped',
    port: 5173,
    icon: 'fa-solid fa-wave-square'
  },
  {
    id: 'stable-audio-3',
    name: 'Stable Audio 3',
    description: 'Text-to-audio generation for music and sound effects',
    status: 'stopped',
    icon: 'fa-solid fa-music'
  },
  {
    id: 'tascar',
    name: 'TASCAR',
    description: 'Spatial audio rendering in Ambisonics and VBAP',
    status: 'stopped',
    icon: 'fa-solid fa-headphones'
  }
]

export function useAudioApps() {
  const [apps, setApps] = useState<AudioApp[]>(MOCK_AUDIO_APPS)
  const [loading, setLoading] = useState(false)

  const refresh = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/audio-apps')
      if (response.ok) {
        const data = await response.json()
        setApps(data)
      }
    } catch {
      // Use mock data if API unavailable
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, 10000)
    return () => clearInterval(interval)
  }, [])

  const launchApp = async (appId: string) => {
    try {
      await fetch(`/api/audio-apps/${appId}/launch`, { method: 'POST' })
      await refresh()
    } catch {
      console.error('Failed to launch app')
    }
  }

  const stopApp = async (appId: string) => {
    try {
      await fetch(`/api/audio-apps/${appId}/stop`, { method: 'POST' })
      await refresh()
    } catch {
      console.error('Failed to stop app')
    }
  }

  return { apps, loading, refresh, launchApp, stopApp }
}
