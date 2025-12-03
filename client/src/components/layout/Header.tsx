import {
	ChevronDown,
	LogOut,
	Settings,
	User,
	Menu,
	PanelLeftClose,
	PanelLeft,
	Terminal,
	Search,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuLabel,
	DropdownMenuSeparator,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/contexts/AuthContext";
import { useScopeStore } from "@/stores/scopeStore";
import { useOrganizations } from "@/hooks/useOrganizations";
import { OrgScopeSwitcher } from "@/components/OrgScopeSwitcher";
import { useEditorStore } from "@/stores/editorStore";
import { useQuickAccessStore } from "@/stores/quickAccessStore";
import { NotificationCenter } from "@/components/layout/NotificationCenter";
import type { components } from "@/lib/v1";
type Organization = components["schemas"]["OrganizationPublic"];

interface HeaderProps {
	onMobileMenuToggle?: () => void;
	onSidebarToggle?: () => void;
	isSidebarCollapsed?: boolean;
}

export function Header({
	onMobileMenuToggle,
	onSidebarToggle,
	isSidebarCollapsed = false,
}: HeaderProps = {}) {
	const { user, logout, isPlatformAdmin } = useAuth();
	const scope = useScopeStore((state) => state.scope);
	const setScope = useScopeStore((state) => state.setScope);
	const isGlobalScope = useScopeStore((state) => state.isGlobalScope);
	const openEditor = useEditorStore((state) => state.openEditor);
	const openQuickAccess = useQuickAccessStore(
		(state) => state.openQuickAccess,
	);

	const userEmail = user?.email || "Loading...";
	const userName = user?.name || user?.email?.split("@")[0] || "User";

	// Only fetch organizations if user is a platform admin
	const { data: organizationData, isLoading: orgsLoading } = useOrganizations(
		{
			enabled: isPlatformAdmin,
		},
	);
	const organizations: Organization[] = Array.isArray(organizationData)
		? organizationData
		: [];

	return (
		<header className="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
			<div className="flex h-16 items-center px-4 lg:px-6">
				{/* Mobile Menu Button */}
				<Button
					variant="ghost"
					size="icon"
					className="md:hidden mr-2"
					onClick={onMobileMenuToggle}
				>
					<Menu className="h-5 w-5" />
				</Button>

				{/* Desktop Sidebar Toggle */}
				<Button
					variant="ghost"
					size="icon"
					className="hidden md:flex mr-2"
					onClick={onSidebarToggle}
					title={
						isSidebarCollapsed
							? "Expand sidebar"
							: "Collapse sidebar"
					}
				>
					{isSidebarCollapsed ? (
						<PanelLeft className="h-5 w-5" />
					) : (
						<PanelLeftClose className="h-5 w-5" />
					)}
				</Button>

				{/* Organization Scope Switcher (Platform Admin only) */}
				{isPlatformAdmin && (
					<div className="mr-2">
						<OrgScopeSwitcher
							scope={scope}
							setScope={setScope}
							organizations={organizations}
							isLoading={orgsLoading}
							isGlobalScope={isGlobalScope}
						/>
					</div>
				)}

				{/* Spacer */}
				<div className="flex-1" />

				{/* Search Button */}
				<Button
					variant="ghost"
					size="icon"
					className="mr-4"
					onClick={() => openQuickAccess()}
					title="Search (Cmd+K)"
				>
					<Search className="h-4 w-4" />
				</Button>

				{/* Shell Button (Platform Admin only) */}
				{isPlatformAdmin && (
					<Button
						variant="ghost"
						size="icon"
						className="mr-4"
						onClick={() => openEditor()}
						title="Shell"
					>
						<Terminal className="h-4 w-4" />
					</Button>
				)}

				{/* Notification Center */}
				<div className="mr-2">
					<NotificationCenter />
				</div>

				{/* Theme Toggle */}
				<div className="mr-2">
					<ThemeToggle />
				</div>

				{/* User Menu */}
				<DropdownMenu>
					<DropdownMenuTrigger asChild>
						<Button variant="ghost" className="gap-2">
							<User className="h-4 w-4" />
							<span className="hidden md:inline-block">
								{userName}
							</span>
							<ChevronDown className="h-4 w-4" />
						</Button>
					</DropdownMenuTrigger>
					<DropdownMenuContent align="end" className="w-56">
						<DropdownMenuLabel>
							<div className="flex flex-col space-y-1">
								<p className="text-sm font-medium">
									{userName}
								</p>
								<p className="text-xs text-muted-foreground">
									{userEmail}
								</p>
							</div>
						</DropdownMenuLabel>
						<DropdownMenuSeparator />
						<DropdownMenuItem>
							<Settings className="mr-2 h-4 w-4" />
							Settings
						</DropdownMenuItem>
						<DropdownMenuSeparator />
						<DropdownMenuItem
							className="text-destructive"
							onClick={logout}
						>
							<LogOut className="mr-2 h-4 w-4" />
							Log out
						</DropdownMenuItem>
					</DropdownMenuContent>
				</DropdownMenu>
			</div>
		</header>
	);
}
