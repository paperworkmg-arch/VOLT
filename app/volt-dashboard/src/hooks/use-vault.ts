import { useQuery } from '@tanstack/react-query'
import { getVaultEntries, getVaultStats, searchVault, getExtractionHistory, type VaultEntry, type VaultStats } from '@/lib/api'

export function useVaultEntries(category?: string) {
  return useQuery<VaultEntry[]>({ queryKey: ['vault', category], queryFn: () => getVaultEntries(category) })
}
export function useVaultStats() {
  return useQuery<VaultStats>({ queryKey: ['vault-stats'], queryFn: getVaultStats })
}
export function useVaultSearch(q: string) {
  return useQuery<VaultEntry[]>({ queryKey: ['vault-search', q], queryFn: () => searchVault(q), enabled: q.length > 1 })
}
export function useExtractionHistory() {
  return useQuery<any[]>({ queryKey: ['extractions'], queryFn: getExtractionHistory })
}
