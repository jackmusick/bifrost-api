import { useEffect, useLayoutEffect, useRef } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
	LayoutDashboard,
	Workflow,
	History,
	Building,
	Users,
	FileCode,
	Key,
	UserCog,
	Settings as SettingsIcon,
	X,
	Stethoscope,
	ShieldCheck,
	MessageSquare,
	Bot,
	Plug,
	DollarSign,
	Activity,
	Webhook,
	Database,
	FolderOpen,
	AppWindow,
	Network,
	BookOpen,
	ServerCog,
	Boxes,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/AuthContext";
import { Logo } from "@/components/branding/Logo";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { term, useTerminology, type ProductTermKey } from "@/lib/terminology";

interface NavItem {
	title: string;
	termKey?: ProductTermKey;
	href: string;
	icon: React.ElementType;
	requiresPlatformAdmin?: boolean;
	dividerBefore?: boolean;
}

interface NavSection {
	title: string;
	items: NavItem[];
	requiresPlatformAdmin?: boolean;
}

const navSections: NavSection[] = [
	{
		title: "Overview",
		requiresPlatformAdmin: true,
		items: [
			{
				title: "Dashboard",
				href: "/",
				icon: LayoutDashboard,
				requiresPlatformAdmin: true,
			},
		],
	},
	{
		title: "Hub",
		items: [
			{
				title: "Chat",
				href: "/chat",
				icon: MessageSquare,
			},
			{
				title: "Apps",
				termKey: "app",
				href: "/apps",
				icon: AppWindow,
			},
			{
				title: "Forms",
				termKey: "form",
				href: "/forms",
				icon: FileCode,
			},
			{
				title: "History",
				href: "/history",
				icon: History,
			},
		],
	},
	{
		title: "Automation",
		items: [
			{
				title: "Agents",
				termKey: "agent",
				href: "/agents",
				icon: Bot,
			},
			{
				title: "Workflows",
				href: "/workflows",
				icon: Workflow,
				requiresPlatformAdmin: true,
			},
		],
	},
	{
		title: "Data",
		requiresPlatformAdmin: true,
		items: [
			{
				title: "Config",
				href: "/config",
				icon: Key,
				requiresPlatformAdmin: true,
			},
			{
				title: "Tables",
				href: "/tables",
				icon: Database,
				requiresPlatformAdmin: true,
			},
			{
				title: "Files",
				href: "/files",
				icon: FolderOpen,
				requiresPlatformAdmin: true,
			},
			{
				title: "Knowledge",
				href: "/knowledge",
				icon: BookOpen,
				requiresPlatformAdmin: true,
			},
			{
				title: "Integrations",
				href: "/integrations",
				icon: Plug,
				requiresPlatformAdmin: true,
			},
			{
				title: "MCP Servers",
				href: "/mcp-servers",
				icon: ServerCog,
				requiresPlatformAdmin: true,
			},
			{
				title: "Events",
				href: "/event-sources",
				icon: Webhook,
				requiresPlatformAdmin: true,
			},
			{
				title: "Entity Management",
				href: "/entity-management",
				icon: Network,
				requiresPlatformAdmin: true,
			},
		],
	},
	{
		title: "Platform",
		requiresPlatformAdmin: true,
		items: [
			{
				title: "Organizations",
				href: "/organizations",
				icon: Building,
				requiresPlatformAdmin: true,
			},
			{
				title: "Users",
				href: "/users",
				icon: Users,
				requiresPlatformAdmin: true,
			},
			{
				title: "Roles",
				href: "/roles",
				icon: UserCog,
				requiresPlatformAdmin: true,
			},
			{
				title: "Solutions",
				href: "/solutions",
				icon: Boxes,
				requiresPlatformAdmin: true,
			},
			{
				title: "Settings",
				href: "/settings",
				icon: SettingsIcon,
				requiresPlatformAdmin: true,
			},
			{
				title: "Diagnostics",
				href: "/diagnostics",
				icon: Stethoscope,
				requiresPlatformAdmin: true,
			},
			{
				title: "Audit Log",
				href: "/audit",
				icon: ShieldCheck,
				requiresPlatformAdmin: true,
			},
		],
	},
	{
		title: "Reports",
		requiresPlatformAdmin: true,
		items: [
			{
				title: "ROI",
				href: "/reports/roi",
				icon: DollarSign,
				requiresPlatformAdmin: true,
			},
			{
				title: "Usage",
				href: "/reports/usage",
				icon: Activity,
				requiresPlatformAdmin: true,
			},
		],
	},
];

interface SidebarProps {
	isMobileMenuOpen: boolean;
	setIsMobileMenuOpen: (open: boolean) => void;
	isCollapsed: boolean;
}

export function Sidebar({
	isMobileMenuOpen,
	setIsMobileMenuOpen,
	isCollapsed,
}: SidebarProps) {
	const { isPlatformAdmin } = useAuth();
	const terminology = useTerminology();
	const location = useLocation();
	const desktopNavRef = useRef<HTMLElement | null>(null);
	const desktopNavScrollTopRef = useRef(0);

	// A mobile modal must not keep the desktop shell inert after a resize.
	useEffect(() => {
		if (!isMobileMenuOpen) return;
		const media = window.matchMedia("(min-width: 768px)");
		const closeOnDesktop = () => {
			if (media.matches) setIsMobileMenuOpen(false);
		};
		closeOnDesktop();
		media.addEventListener("change", closeOnDesktop);
		return () => media.removeEventListener("change", closeOnDesktop);
	}, [isMobileMenuOpen, setIsMobileMenuOpen]);

	// Filter sections and items based on user permissions
	const visibleSections = navSections
		.filter((section) => !section.requiresPlatformAdmin || isPlatformAdmin)
		.map((section) => ({
			...section,
			items: section.items.filter(
				(item) => !item.requiresPlatformAdmin || isPlatformAdmin,
			),
		}))
		.filter((section) => section.items.length > 0); // Remove empty sections

	useLayoutEffect(() => {
		const nav = desktopNavRef.current;
		if (!nav) return;
		nav.scrollTop = desktopNavScrollTopRef.current;
	}, [location.pathname, location.search]);

	return (
		<>
			{/* Desktop Sidebar */}
			<aside
				className={cn(
					"bf-platform-rail relative hidden md:flex shrink-0 flex-col h-dvh border-r bg-sidebar transition-[width] duration-200 motion-reduce:transition-none",
					isCollapsed ? "w-16" : "w-[248px]",
				)}
			>
				{/* Logo Section */}
				<div
					className={cn(
						"h-16 flex items-center border-b",
						isCollapsed
							? "justify-center px-4"
							: "justify-start px-7",
					)}
				>
					{isCollapsed ? (
						<Logo type="square" className="h-10 w-10" alt="Logo" />
					) : (
						<Logo type="rectangle" className="h-8" alt="Logo" />
					)}
				</div>

				{/* Navigation */}
				<nav
					ref={desktopNavRef}
					aria-label="Primary navigation"
					className={cn(
						"flex-1 flex flex-col gap-4 overflow-y-auto",
						isCollapsed ? "px-2 py-4" : "p-4",
					)}
					onScroll={(event) => {
						desktopNavScrollTopRef.current =
							event.currentTarget.scrollTop;
					}}
				>
					{visibleSections.map((section) => (
						<div key={section.title} className="space-y-1">
							{!isCollapsed && (
								<h3 className="text-xs font-semibold text-muted-foreground mb-2 px-3 uppercase tracking-wider">
									{section.title}
								</h3>
							)}
							{section.items.map((item) => {
								const Icon = item.icon;
								const itemTitle = item.termKey
									? term(terminology, item.termKey, "plural")
									: item.title;
								return (
									<div key={item.href}>
										{item.dividerBefore && !isCollapsed && (
											<div className="my-2 mx-3 border-t border-border" />
										)}
										{item.dividerBefore && isCollapsed && (
											<div className="my-2 mx-2 border-t border-border" />
										)}
										<NavLink
											to={item.href}
											aria-label={itemTitle}
											title={
												isCollapsed
													? itemTitle
													: undefined
											}
											className={({ isActive }) =>
												cn(
													"flex min-h-10 items-center border-l-2 rounded-none text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-2",
													"hover:bg-accent hover:text-accent-foreground",
													isActive
														? "border-primary bg-primary/[0.07] text-primary"
														: "border-transparent text-muted-foreground",
													isCollapsed
														? "justify-center w-10 h-10 mx-auto"
														: "gap-3 px-3 py-2",
												)
											}
										>
											<Icon
												className={cn(
													isCollapsed
														? "h-5 w-5 shrink-0"
														: "h-4 w-4 shrink-0",
												)}
											/>
											{!isCollapsed && (
												<span className="min-w-0 break-words">
													{itemTitle}
												</span>
											)}
										</NavLink>
									</div>
								);
							})}
						</div>
					))}
				</nav>
			</aside>

			{/* Mobile Sidebar Overlay */}
			<Sheet open={isMobileMenuOpen} onOpenChange={setIsMobileMenuOpen}>
				<SheetContent
					side="left"
					showCloseButton={false}
					className="bf-platform-rail w-[min(20rem,calc(100vw-2rem))] gap-0 bg-sidebar"
					aria-describedby={undefined}
					onCloseAutoFocus={(event) => {
						event.preventDefault();
						document
							.querySelector<HTMLElement>(
								"[data-mobile-navigation-trigger]",
							)
							?.focus();
					}}
				>
					<SheetTitle className="sr-only">Navigation</SheetTitle>
					{/* Logo Section with Close Button */}
					<div className="h-16 flex items-center justify-between border-b px-4">
						<Logo type="rectangle" className="h-8" alt="Logo" />
						<Button
							variant="ghost"
							size="icon"
							onClick={() => setIsMobileMenuOpen(false)}
							aria-label="Close navigation"
						>
							<X className="h-5 w-5" />
						</Button>
					</div>

					{/* Navigation */}
					<nav
						aria-label="Primary navigation"
						className="flex-1 min-h-0 flex flex-col gap-4 p-4 overflow-y-auto"
					>
						{visibleSections.map((section) => (
							<div key={section.title} className="space-y-1">
								<h3 className="text-xs font-semibold text-muted-foreground mb-2 px-3 uppercase tracking-wider">
									{section.title}
								</h3>
								{section.items.map((item) => {
									const Icon = item.icon;
									const itemTitle = item.termKey
										? term(
												terminology,
												item.termKey,
												"plural",
											)
										: item.title;
									return (
										<div key={item.href}>
											{item.dividerBefore && (
												<div className="my-2 mx-3 border-t border-border" />
											)}
											<NavLink
												to={item.href}
												aria-label={itemTitle}
												onClick={() =>
													setIsMobileMenuOpen(false)
												}
												className={({ isActive }) =>
													cn(
														"flex min-h-11 items-center gap-3 border-l-2 px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-ring",
														"hover:bg-accent hover:text-accent-foreground",
														isActive
															? "border-primary bg-primary/[0.07] text-primary"
															: "border-transparent text-muted-foreground",
													)
												}
											>
												<Icon className="h-4 w-4 shrink-0" />
												{itemTitle}
											</NavLink>
										</div>
									);
								})}
							</div>
						))}
					</nav>
				</SheetContent>
			</Sheet>
		</>
	);
}
