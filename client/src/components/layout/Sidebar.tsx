import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Workflow,
  History,
  Building,
  Users,
  FileCode,
  Key,
  UserCog,
  Shield,
  BookOpen,
  Link2,
  Clock,
  Settings as SettingsIcon,
  X,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useHealthStore } from '@/stores/healthStore'
import { useAuth } from '@/hooks/useAuth'
import { Logo } from '@/components/branding/Logo'
import { Button } from '@/components/ui/button'

interface NavItem {
  title: string
  href: string
  icon: React.ElementType
  requiresWorkflowEngine?: boolean
  requiresPlatformAdmin?: boolean
}

interface NavSection {
  title: string
  items: NavItem[]
  requiresPlatformAdmin?: boolean
}

const navSections: NavSection[] = [
  {
    title: 'Overview',
    requiresPlatformAdmin: true,
    items: [
      {
        title: 'Dashboard',
        href: '/',
        icon: LayoutDashboard,
        requiresPlatformAdmin: true,
      },
    ],
  },
  {
    title: 'Automation',
    items: [
      {
        title: 'Forms',
        href: '/forms',
        icon: FileCode,
        requiresWorkflowEngine: true,
      },
      {
        title: 'Workflows',
        href: '/workflows',
        icon: Workflow,
        requiresWorkflowEngine: true,
        requiresPlatformAdmin: true,
      },
      {
        title: 'History',
        href: '/history',
        icon: History,
        requiresWorkflowEngine: true,
      },
    ],
  },
  {
    title: 'Configuration',
    requiresPlatformAdmin: true,
    items: [
      {
        title: 'Settings',
        href: '/settings',
        icon: SettingsIcon,
        requiresPlatformAdmin: true,
      },
      {
        title: 'Config',
        href: '/config',
        icon: Key,
        requiresPlatformAdmin: true,
      },
      {
        title: 'Secrets',
        href: '/secrets',
        icon: Shield,
        requiresPlatformAdmin: true,
      },
      {
        title: 'OAuth',
        href: '/oauth',
        icon: Link2,
        requiresPlatformAdmin: true,
      },
      {
        title: 'Schedules',
        href: '/schedules',
        icon: Clock,
        requiresPlatformAdmin: true,
        requiresWorkflowEngine: true,
      },
    ],
  },
  {
    title: 'Administration',
    requiresPlatformAdmin: true,
    items: [
      {
        title: 'Organizations',
        href: '/organizations',
        icon: Building,
        requiresPlatformAdmin: true,
      },
      {
        title: 'Users',
        href: '/users',
        icon: Users,
        requiresPlatformAdmin: true,
      },
      {
        title: 'Roles',
        href: '/roles',
        icon: UserCog,
        requiresPlatformAdmin: true,
      },
    ],
  },
  {
    title: 'Resources',
    requiresPlatformAdmin: true,
    items: [
      {
        title: 'Docs',
        href: '/docs',
        icon: BookOpen,
        requiresPlatformAdmin: true,
      },
    ],
  },
]

interface SidebarProps {
  isMobileMenuOpen: boolean
  setIsMobileMenuOpen: (open: boolean) => void
  isCollapsed: boolean
}

export function Sidebar({ isMobileMenuOpen, setIsMobileMenuOpen, isCollapsed }: SidebarProps) {
  const healthStatus = useHealthStore((state) => state.status)
  const isServerUnhealthy = healthStatus === 'unhealthy'
  const { isPlatformAdmin } = useAuth()

  // Filter sections and items based on user permissions
  const visibleSections = navSections
    .filter((section) => !section.requiresPlatformAdmin || isPlatformAdmin)
    .map((section) => ({
      ...section,
      items: section.items.filter(
        (item) => !item.requiresPlatformAdmin || isPlatformAdmin
      ),
    }))
    .filter((section) => section.items.length > 0) // Remove empty sections

  return (
    <>
      {/* Desktop Sidebar */}
      <aside className={cn(
        "hidden md:flex flex-col h-screen border-r bg-background transition-all duration-300",
        isCollapsed ? "w-16" : "w-64"
      )}>
        {/* Logo Section */}
        <div className={cn(
          "h-16 flex items-center border-b",
          isCollapsed ? "justify-center px-4" : "justify-start px-7"
        )}>
          {isCollapsed ? (
            <Logo type="square" className="h-10 w-10" alt="Logo" />
          ) : (
            <Logo type="rectangle" className="h-8" alt="Logo" />
          )}
        </div>

        {/* Navigation */}
        <nav className={cn(
          "flex-1 flex flex-col gap-4 overflow-y-auto",
          isCollapsed ? "px-2 py-4" : "p-4"
        )}>
        {visibleSections.map((section) => (
          <div key={section.title} className="space-y-1">
            {!isCollapsed && (
              <h3 className="text-xs font-semibold text-muted-foreground mb-2 px-3 uppercase tracking-wider">
                {section.title}
              </h3>
            )}
            {section.items.map((item) => {
              const Icon = item.icon
              const isDisabled = item.requiresWorkflowEngine && isServerUnhealthy

              if (isDisabled) {
                return (
                  <div
                    key={item.href}
                    className={cn(
                      'flex items-center rounded-lg text-sm font-medium',
                      'text-muted-foreground/50 cursor-not-allowed opacity-50',
                      isCollapsed ? 'justify-center w-10 h-10 mx-auto' : 'gap-3 px-3 py-2'
                    )}
                    title="Workflow engine unavailable"
                  >
                    <Icon className={cn(isCollapsed ? 'h-5 w-5' : 'h-4 w-4')} />
                    {!isCollapsed && item.title}
                  </div>
                )
              }

              return (
                <NavLink
                  key={item.href}
                  to={item.href}
                  title={isCollapsed ? item.title : undefined}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center rounded-lg text-sm font-medium transition-colors',
                      'hover:bg-accent hover:text-accent-foreground',
                      isActive
                        ? 'bg-accent text-accent-foreground'
                        : 'text-muted-foreground',
                      isCollapsed ? 'justify-center w-10 h-10 mx-auto' : 'gap-3 px-3 py-2'
                    )
                  }
                >
                  <Icon className={cn(isCollapsed ? 'h-5 w-5' : 'h-4 w-4')} />
                  {!isCollapsed && item.title}
                </NavLink>
              )
            })}
          </div>
        ))}
        </nav>
      </aside>

      {/* Mobile Sidebar Overlay */}
      {isMobileMenuOpen && (
        <div
          className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm md:hidden"
          onClick={() => setIsMobileMenuOpen(false)}
        >
          <aside
            className="fixed left-0 top-0 h-screen w-64 border-r bg-background flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Logo Section with Close Button */}
            <div className="h-16 flex items-center justify-between border-b px-4">
              <Logo type="rectangle" className="h-8" alt="Logo" />
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setIsMobileMenuOpen(false)}
              >
                <X className="h-5 w-5" />
              </Button>
            </div>

            {/* Navigation */}
            <nav className="flex-1 flex flex-col gap-4 p-4 overflow-y-auto">
              {visibleSections.map((section) => (
                <div key={section.title} className="space-y-1">
                  <h3 className="text-xs font-semibold text-muted-foreground mb-2 px-3 uppercase tracking-wider">
                    {section.title}
                  </h3>
                  {section.items.map((item) => {
                    const Icon = item.icon
                    const isDisabled = item.requiresWorkflowEngine && isServerUnhealthy

                    if (isDisabled) {
                      return (
                        <div
                          key={item.href}
                          className={cn(
                            'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium',
                            'text-muted-foreground/50 cursor-not-allowed opacity-50'
                          )}
                          title="Workflow engine unavailable"
                        >
                          <Icon className="h-4 w-4" />
                          {item.title}
                        </div>
                      )
                    }

                    return (
                      <NavLink
                        key={item.href}
                        to={item.href}
                        onClick={() => setIsMobileMenuOpen(false)}
                        className={({ isActive }) =>
                          cn(
                            'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                            'hover:bg-accent hover:text-accent-foreground',
                            isActive
                              ? 'bg-accent text-accent-foreground'
                              : 'text-muted-foreground'
                          )
                        }
                      >
                        <Icon className="h-4 w-4" />
                        {item.title}
                      </NavLink>
                    )
                  })}
                </div>
              ))}
            </nav>
          </aside>
        </div>
      )}
    </>
  )
}
