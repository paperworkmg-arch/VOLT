import { useQuery } from '@tanstack/react-query'
import { getAgents, type Agent } from '@/lib/api'

export function useAgents() {
  return useQuery<Agent[]>({ queryKey: ['agents'], queryFn: getAgents })
}
