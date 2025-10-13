/**
 * User Context Provider
 * Provides global access to user information (orgId, userId, permissions)
 */

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

interface UserContextType {
  userId: string
  email: string
  displayName: string
  orgId: string | null
  setOrgId: (orgId: string) => void
  isLoading: boolean
}

const UserContext = createContext<UserContextType | undefined>(undefined)

interface UserProviderProps {
  children: ReactNode
}

export function UserProvider({ children }: UserProviderProps) {
  const [userId] = useState('test-user-123') // TODO: Get from auth
  const [email] = useState('admin@msp.com') // TODO: Get from auth
  const [displayName] = useState('Test Admin') // TODO: Get from auth
  const [orgId, setOrgIdState] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Initialize orgId from localStorage if available
    const storedOrgId = localStorage.getItem('selectedOrgId')
    if (storedOrgId) {
      setOrgIdState(storedOrgId)
    }
    // No default - orgId can be null (for GLOBAL scope)
    setIsLoading(false)
  }, [])

  const setOrgId = (newOrgId: string) => {
    setOrgIdState(newOrgId)
    localStorage.setItem('selectedOrgId', newOrgId)
  }

  return (
    <UserContext.Provider
      value={{
        userId,
        email,
        displayName,
        orgId,
        setOrgId,
        isLoading,
      }}
    >
      {children}
    </UserContext.Provider>
  )
}

export function useUser() {
  const context = useContext(UserContext)
  if (context === undefined) {
    throw new Error('useUser must be used within a UserProvider')
  }
  return context
}
