import { useQuery } from '@tanstack/react-query'
import { getSamples, getSampleStats, type Sample, type SampleStats } from '@/lib/api'

export function useSamples(params?: Record<string, string>) {
  return useQuery<Sample[]>({ queryKey: ['samples', params], queryFn: () => getSamples(params) })
}
export function useSampleStats() {
  return useQuery<SampleStats>({ queryKey: ['sample-stats'], queryFn: getSampleStats })
}
