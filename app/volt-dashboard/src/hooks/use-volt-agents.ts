import { useState, useEffect } from 'react'

interface VoltAgent {
  id: string
  name: string
  description: string
  icon: string
  color: string
  installed: boolean
  running: boolean
  metrics: Record<string, number>
  recent_logs: string[]
  script: string
}

interface PipelineStats {
  incoming_leads: number
  outbound_pitches: number
  send_queue: number
  sent: number
  closed_deals: number
  skipped: number
}

const MOCK_AGENTS: VoltAgent[] = [
  {
    id: 'studio_agent',
    name: 'Studio Agent',
    description: 'Lead processor - watches for new inbound leads, extracts facts, computes deals, writes pitches',
    icon: 'fa-solid fa-microphone',
    color: 'amber',
    installed: true,
    running: false,
    metrics: { pending_leads: 12, closed_deals: 8 },
    recent_logs: [],
    script: 'studio_agent.py'
  },
  {
    id: 'inbound_agent',
    name: 'Inbound Agent',
    description: 'Handles incoming email replies from artists, auto-responds to inquiries',
    icon: 'fa-solid fa-inbox',
    color: 'emerald',
    installed: true,
    running: false,
    metrics: {},
    recent_logs: [],
    script: 'inbound_agent.py'
  },
  {
    id: 'contact_enricher',
    name: 'Contact Enricher',
    description: 'Enriches pitch files with artist contact info (Instagram, X, email)',
    icon: 'fa-solid fa-address-book',
    color: 'blue',
    installed: true,
    running: false,
    metrics: {},
    recent_logs: [],
    script: 'contact_enricher.py'
  },
  {
    id: 'send_queue',
    name: 'Send Queue',
    description: 'Drafts Instagram DMs and emails for enriched pitches, queues for approval',
    icon: 'fa-solid fa-paper-plane',
    color: 'violet',
    installed: true,
    running: false,
    metrics: { queued: 5 },
    recent_logs: [],
    script: 'send_queue.py'
  },
  {
    id: 'approved_sender',
    name: 'Approved Sender',
    description: 'Sends approved emails via Gmail SMTP, watches Send_Queue/Approved/',
    icon: 'fa-solid fa-check-circle',
    color: 'green',
    installed: true,
    running: false,
    metrics: { sent: 23 },
    recent_logs: [],
    script: 'approved_sender.py'
  },
  {
    id: 'ghost_followup',
    name: 'Ghost Follow-Up',
    description: 'Follows up with artists who haven\'t replied to pitches after 48 hours',
    icon: 'fa-solid fa-ghost',
    color: 'orange',
    installed: true,
    running: false,
    metrics: { pending_followups: 15 },
    recent_logs: [],
    script: 'ghost_followup.py'
  },
  {
    id: 'instagram_coldlist',
    name: 'Instagram Cold Outreach',
    description: 'Cold DMs to Instagram followers, drafts personalized messages',
    icon: 'fa-brands fa-instagram',
    color: 'pink',
    installed: true,
    running: false,
    metrics: {},
    recent_logs: [],
    script: 'instagram_coldlist.py'
  },
  {
    id: 'music_library_aggregator',
    name: 'Music Library Aggregator',
    description: 'A&R lead discovery via LinkedIn for APM/UPM sub-libraries',
    icon: 'fa-solid fa-music',
    color: 'cyan',
    installed: true,
    running: false,
    metrics: {},
    recent_logs: [],
    script: 'music_library_aggregator.py'
  }
]

const MOCK_PIPELINE: PipelineStats = {
  incoming_leads: 47,
  outbound_pitches: 32,
  send_queue: 8,
  sent: 24,
  closed_deals: 12,
  skipped: 15
}

export function useVoltAgents() {
  const [agents, setAgents] = useState<VoltAgent[]>(MOCK_AGENTS)
  const [pipeline, setPipeline] = useState<PipelineStats>(MOCK_PIPELINE)
  const [loading, setLoading] = useState(false)

  const refresh = async () => {
    setLoading(true)
    try {
      const [agentsRes, pipelineRes] = await Promise.all([
        fetch('/api/volt-agents'),
        fetch('/api/pipeline/stats')
      ])
      if (agentsRes.ok) {
        const agentsData = await agentsRes.json()
        setAgents(agentsData)
      }
      if (pipelineRes.ok) {
        const pipelineData = await pipelineRes.json()
        setPipeline(pipelineData)
      }
    } catch {
      // Use mock data if API unavailable
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, 15000)
    return () => clearInterval(interval)
  }, [])

  const runAgent = async (agentId: string) => {
    try {
      await fetch(`/api/volt-agents/${agentId}/run`, { method: 'POST' })
      await refresh()
    } catch {
      console.error('Failed to run agent')
    }
  }

  const stopAgent = async (agentId: string) => {
    try {
      await fetch(`/api/volt-agents/${agentId}/stop`, { method: 'POST' })
      await refresh()
    } catch {
      console.error('Failed to stop agent')
    }
  }

  return { agents, pipeline, loading, refresh, runAgent, stopAgent }
}
