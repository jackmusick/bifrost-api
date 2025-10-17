import { Outlet } from 'react-router-dom'
import { Header } from './Header'
import { Sidebar } from './Sidebar'
import { useAuth } from '@/hooks/useAuth'
import { NoAccess } from '@/components/NoAccess'
import { Skeleton } from '@/components/ui/skeleton'

export function Layout() {
  const { isLoading, isPlatformAdmin, isOrgUser } = useAuth()

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="flex">
          <main className="flex-1 p-6 lg:p-8">
            <div className="space-y-6">
              <Skeleton className="h-12 w-64" />
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {[...Array(6)].map((_, i) => (
                  <Skeleton key={i} className="h-64 w-full" />
                ))}
              </div>
            </div>
          </main>
        </div>
      </div>
    )
  }

  // Show no access page if user has no role (only authenticated, no PlatformAdmin or OrgUser)
  const hasAccess = isPlatformAdmin || isOrgUser
  if (!hasAccess) {
    return <NoAccess />
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="flex">
        <Sidebar />
        <main className="flex-1 p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
