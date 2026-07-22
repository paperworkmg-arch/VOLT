import { useQuery } from '@tanstack/react-query'
import { getTasks, type Task } from '@/lib/api'

export function useTasks() {
  return useQuery<Task[]>({ queryKey: ['tasks'], queryFn: getTasks })
}
