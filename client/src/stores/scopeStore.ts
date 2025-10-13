import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

export interface OrgScope {
  type: 'global' | 'organization'
  orgId: string | null
  orgName: string | null
}

interface ScopeState {
  scope: OrgScope
  isGlobalScope: boolean
  _hasHydrated: boolean
  setScope: (scope: OrgScope) => void
  setHasHydrated: (hydrated: boolean) => void
}

// Helper to sync sessionStorage
const syncSessionStorage = (scope: OrgScope) => {
  console.log('[scopeStore] syncSessionStorage called with:', scope)
  if (scope.orgId) {
    sessionStorage.setItem('current_org_id', scope.orgId)
    console.log('[scopeStore] Set sessionStorage current_org_id to:', scope.orgId)
  } else {
    sessionStorage.removeItem('current_org_id')
    console.log('[scopeStore] Removed sessionStorage current_org_id')
  }
}

export const useScopeStore = create<ScopeState>()(
  persist(
    (set, get) => ({
      scope: { type: 'global', orgId: null, orgName: null },
      isGlobalScope: true,
      _hasHydrated: false,
      setScope: (scope) => {
        // Update sessionStorage for API client
        syncSessionStorage(scope)

        set({
          scope,
          isGlobalScope: scope.type === 'global',
        })
      },
      setHasHydrated: (hydrated) => {
        set({ _hasHydrated: hydrated })
      },
    }),
    {
      name: 'msp-automation-org-scope',
      storage: createJSONStorage(() => localStorage),
      // On rehydration (initial load from localStorage), sync sessionStorage
      onRehydrateStorage: () => (state, error) => {
        console.log('[scopeStore] onRehydrateStorage callback - state:', state, 'error:', error)
        if (!error && state) {
          // Sync sessionStorage immediately when rehydrating
          console.log('[scopeStore] About to sync sessionStorage with rehydrated scope')
          syncSessionStorage(state.scope)
          // Mark as hydrated
          console.log('[scopeStore] Setting _hasHydrated to true')
          useScopeStore.setState({ _hasHydrated: true })
        }
      },
    }
  )
)
