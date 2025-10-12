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
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useWorkflowEngineHealth } from '@/hooks/useWorkflowEngineHealth'

interface NavItem {
  title: string
  href: string
  icon: React.ElementType
  requiresWorkflowEngine?: boolean
}

const navItems: NavItem[] = [
  {
    title: 'Dashboard',
    href: '/',
    icon: LayoutDashboard,
  },
  {
    title: 'Workflows',
    href: '/workflows',
    icon: Workflow,
    requiresWorkflowEngine: true,
  },
  {
    title: 'Forms',
    href: '/forms',
    icon: FileCode,
    requiresWorkflowEngine: true,
  },
  {
    title: 'History',
    href: '/history',
    icon: History,
    requiresWorkflowEngine: true,
  },
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
    title: 'Docs',
    href: '/docs',
    icon: BookOpen,
  },
  {
    title: 'Settings',
    href: '/settings',
    icon: SettingsIcon,
  },
]

export function Sidebar() {
  const { data: engineHealth } = useWorkflowEngineHealth()
  const isEngineHealthy = engineHealth?.status === 'healthy'

  return (
    <aside className="sticky top-16 h-[calc(100vh-4rem)] w-64 border-r bg-background">
      <nav className="flex h-full flex-col gap-1 p-4 overflow-y-auto">
        {navItems.map((item) => {
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
      </nav>
    </aside>
  )
}
