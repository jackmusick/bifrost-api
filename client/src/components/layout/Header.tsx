import { Building2, ChevronDown, LogOut, Settings, User } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { ThemeToggle } from '@/components/theme-toggle'
import { useAuth, logout } from '@/hooks/useAuth'
import { useOrgScope } from '@/contexts/OrgScopeContext'
import { useOrganizations } from '@/hooks/useOrganizations'
import { OrgScopeSwitcher } from '@/components/OrgScopeSwitcher'

export function Header() {
  const { user } = useAuth()
  const { scope, setScope, isGlobalScope } = useOrgScope()
  const { data: organizations, isLoading: orgsLoading } = useOrganizations()

  const userEmail = user?.userDetails || 'Loading...'
  const userName = user?.userDetails?.split('@')[0] || 'User'

  // Check if user is platform admin
  const isPlatformAdmin = user?.userDetails === 'jack@gocovi.com' // TODO: Get from user profile

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-16 items-center px-6 lg:px-8">
        {/* Logo */}
        <div className="flex items-center gap-2 font-semibold">
          <Building2 className="h-6 w-6" />
          <span className="hidden sm:inline-block">MSP Automation</span>
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Organization Scope Switcher (Platform Admin only) */}
        {isPlatformAdmin && (
          <div className="mr-4">
            <OrgScopeSwitcher
              scope={scope}
              setScope={setScope}
              organizations={organizations}
              isLoading={orgsLoading}
              isGlobalScope={isGlobalScope}
            />
          </div>
        )}

        {/* Theme Toggle */}
        <div className="mr-2">
          <ThemeToggle />
        </div>

        {/* User Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="gap-2">
              <User className="h-4 w-4" />
              <span className="hidden md:inline-block">{userName}</span>
              <ChevronDown className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium">{userName}</p>
                <p className="text-xs text-muted-foreground">{userEmail}</p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <Settings className="mr-2 h-4 w-4" />
              Settings
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-destructive" onClick={logout}>
              <LogOut className="mr-2 h-4 w-4" />
              Log out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
