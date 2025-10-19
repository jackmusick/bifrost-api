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
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useHealthStore } from '@/stores/healthStore'
import { useAuth } from '@/hooks/useAuth'

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
        title: 'API Keys',
        href: '/workflow-keys',
        icon: Key,
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

export function Sidebar() {
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
    <aside className="sticky top-16 h-[calc(100vh-4rem)] w-64 border-r bg-background">
      <nav className="flex h-full flex-col gap-4 p-4 overflow-y-auto">
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
  )
}
