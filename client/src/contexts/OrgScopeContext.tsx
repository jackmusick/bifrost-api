import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

export interface OrgScope {
  type: 'global' | 'organization'
  orgId: string | null
  orgName: string | null
}

interface OrgScopeContextType {
  scope: OrgScope
  setScope: (scope: OrgScope) => void
  isGlobalScope: boolean
}

const OrgScopeContext = createContext<OrgScopeContextType | undefined>(undefined)

const SCOPE_STORAGE_KEY = 'msp-automation-org-scope'

export function OrgScopeProvider({ children }: { children: ReactNode }) {
  const [scope, setScope] = useState<OrgScope>(() => {
    // Load from localStorage on init
    const stored = localStorage.getItem(SCOPE_STORAGE_KEY)
    if (stored) {
      try {
        return JSON.parse(stored)
      } catch {
        // Fall through to default
      }
    }
    return { type: 'global', orgId: null, orgName: null }
  })

  // Persist to localStorage and sessionStorage when scope changes
  useEffect(() => {
    localStorage.setItem(SCOPE_STORAGE_KEY, JSON.stringify(scope))

    // Update sessionStorage for API client (used by api.ts for X-Organization-Id header)
    if (scope.orgId) {
      sessionStorage.setItem('current_org_id', scope.orgId)
    } else {
      // Remove org ID from sessionStorage when in Global scope
      sessionStorage.removeItem('current_org_id')
    }
  }, [scope])

  const isGlobalScope = scope.type === 'global'

  return (
    <OrgScopeContext.Provider value={{ scope, setScope, isGlobalScope }}>
      {children}
    </OrgScopeContext.Provider>
  )
}

export function useOrgScope() {
  const context = useContext(OrgScopeContext)
  if (!context) {
    throw new Error('useOrgScope must be used within OrgScopeProvider')
  }
  return context
}
