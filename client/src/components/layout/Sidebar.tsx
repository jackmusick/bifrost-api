import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Workflow,
  History,
  Building,
  Users,
  FileCode,
  Settings as SettingsIcon,
  Key,
  UserCog,
  Shield,
  BookOpen,
  Link2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useWorkflowEngineHealth } from '@/hooks/useWorkflowEngineHealth'

interface NavItem {
  title: string
  href: string
  icon: React.ElementType
  requiresWorkflowEngine?: boolean
}

interface NavSection {
  title: string
  items: NavItem[]
}

const navSections: NavSection[] = [
  {
    title: 'Overview',
    items: [
      {
        title: 'Dashboard',
        href: '/',
        icon: LayoutDashboard,
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
    items: [
      {
        title: 'Config',
        href: '/config',
        icon: Key,
      },
      {
        title: 'Secrets',
        href: '/secrets',
        icon: Shield,
      },
      {
        title: 'OAuth',
        href: '/oauth',
        icon: Link2,
      },
    ],
  },
  {
    title: 'Administration',
    items: [
      {
        title: 'Organizations',
        href: '/organizations',
        icon: Building,
      },
      {
        title: 'Users',
        href: '/users',
        icon: Users,
      },
      {
        title: 'Roles',
        href: '/roles',
        icon: UserCog,
      },
    ],
  },
  {
    title: 'Resources',
    items: [
      {
        title: 'Docs',
        href: '/docs',
        icon: BookOpen,
      },
      {
        title: 'Settings',
        href: '/settings',
        icon: SettingsIcon,
      },
    ],
  },
]

export function Sidebar() {
  const { data: engineHealth } = useWorkflowEngineHealth()
  const isEngineHealthy = engineHealth?.status === 'healthy'

  return (
    <aside className="sticky top-16 h-[calc(100vh-4rem)] w-64 border-r bg-background">
      <nav className="flex h-full flex-col gap-4 p-4 overflow-y-auto">
        {navSections.map((section) => (
          <div key={section.title} className="space-y-1">
            <h3 className="text-xs font-semibold text-muted-foreground mb-2 px-3 uppercase tracking-wider">
              {section.title}
            </h3>
            {section.items.map((item) => {
              const Icon = item.icon
              const isDisabled = item.requiresWorkflowEngine && !isEngineHealthy

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
