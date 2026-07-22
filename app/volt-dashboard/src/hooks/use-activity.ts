import { useQuery } from '@tanstack/react-query'
import { getActivity, type Activity } from '@/lib/api'

export function useActivity() {
  return useQuery<Activity[]>({ queryKey: ['activity'], queryFn: getActivity, refetchInterval: 5_000 })
}
