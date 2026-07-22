import { useQuery } from '@tanstack/react-query'
import { getSwarmRuns, type SwarmRun } from '@/lib/api'

export function useSwarmRuns() {
  return useQuery<SwarmRun[]>({ queryKey: ['swarm-runs'], queryFn: getSwarmRuns })
}
