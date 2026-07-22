import { useQuery } from '@tanstack/react-query'
import { getSystemHealth, getCleanerStatus, getNotifications, type SystemHealth, type Activity } from '@/lib/api'

export function useSystemHealth() {
  return useQuery<SystemHealth>({ queryKey: ['system-health'], queryFn: getSystemHealth, refetchInterval: 15_000 })
}
export function useCleanerStatus() {
  return useQuery<{usage_gb:number;limit_gb:number;percent:number}>({ queryKey: ['cleaner'], queryFn: getCleanerStatus })
}
export function useNotifications() {
  return useQuery<Activity[]>({ queryKey: ['notifications'], queryFn: getNotifications })
}
