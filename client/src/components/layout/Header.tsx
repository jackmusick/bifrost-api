import {
    ChevronDown,
    LogOut,
    Settings,
    User,
    Circle,
    RefreshCw,
    Menu,
    PanelLeftClose,
    PanelLeft,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth, logout } from "@/hooks/useAuth";
import { useScopeStore } from "@/stores/scopeStore";
import { useOrganizations } from "@/hooks/useOrganizations";
import { OrgScopeSwitcher } from "@/components/OrgScopeSwitcher";
import { useWorkflowEngineHealth } from "@/hooks/useWorkflowEngineHealth";
import { useHealthStore } from "@/stores/healthStore";
import type { components } from "@/lib/v1";
type Organization = components["schemas"]["Organization"];

interface HeaderProps {
    onMobileMenuToggle?: () => void;
    onSidebarToggle?: () => void;
    isSidebarCollapsed?: boolean;
}

export function Header({ onMobileMenuToggle, onSidebarToggle, isSidebarCollapsed = false }: HeaderProps = {}) {
    const navigate = useNavigate();
    const { user } = useAuth();
    const scope = useScopeStore((state) => state.scope);
    const setScope = useScopeStore((state) => state.setScope);
    const isGlobalScope = useScopeStore((state) => state.isGlobalScope);

    const userEmail = user?.userDetails || "Loading...";
    const userName = user?.userDetails?.split("@")[0] || "User";

    // Check if user is platform admin
    const isPlatformAdmin = user?.userRoles?.includes("PlatformAdmin") ?? false;

    // Only fetch organizations if user is a platform admin
    const { data: organizationData, isLoading: orgsLoading } = useOrganizations({
        enabled: isPlatformAdmin
    });
    const organizations: Organization[] = Array.isArray(organizationData) ? organizationData : [];

    // Get health status from store and query
    const healthStatus = useHealthStore((state) => state.status);
    const { refetch, isRefetching } = useWorkflowEngineHealth();

    // Determine status color and message based on store state
    const getServerStatus = () => {
        if (healthStatus === "checking" || isRefetching) {
            return {
                color: "text-yellow-500",
                status: "checking",
                message: "Checking server status...",
                canClick: false,
            };
        }

        if (healthStatus === "healthy") {
            return {
                color: "text-green-500",
                status: "healthy",
                message: "Server is healthy",
                canClick: true,
            };
        }

        if (healthStatus === "unhealthy") {
            return {
                color: "text-red-500",
                status: "unhealthy",
                message: "Server is unavailable",
                canClick: true,
            };
        }

        // Unknown state - hasn't been checked yet
        return {
            color: "text-gray-500",
            status: "unknown",
            message: "Server status unknown",
            canClick: true,
        };
    };

    const serverStatus = getServerStatus();

    const handleStatusClick = () => {
        if (serverStatus.status === "unhealthy") {
            navigate("/workflow-engine-error");
        } else if (serverStatus.canClick) {
            refetch();
        }
    };

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
                    title={isSidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
                >
                    {isSidebarCollapsed ? (
                        <PanelLeft className="h-5 w-5" />
                    ) : (
                        <PanelLeftClose className="h-5 w-5" />
                    )}
                </Button>

                {/* Spacer */}
                <div className="flex-1" />

                {/* Server Status Indicator */}
                <TooltipProvider>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Button
                                variant="ghost"
                                size="sm"
                                className={`mr-4 gap-2 ${
                                    serverStatus.canClick
                                        ? "cursor-pointer"
                                        : "cursor-default"
                                }`}
                                onClick={handleStatusClick}
                                disabled={!serverStatus.canClick}
                            >
                                {isRefetching ? (
                                    <RefreshCw className="h-4 w-4 animate-spin text-yellow-500" />
                                ) : (
                                    <Circle
                                        className={`h-4 w-4 fill-current ${serverStatus.color}`}
                                    />
                                )}
                                <span className="hidden sm:inline-block text-sm">
                                    Server
                                </span>
                            </Button>
                        </TooltipTrigger>
                        <TooltipContent>
                            <p>{serverStatus.message}</p>
                            {serverStatus.status === "healthy" && (
                                <p className="text-xs text-muted-foreground mt-1">
                                    Click to refresh
                                </p>
                            )}
                            {serverStatus.status === "unhealthy" && (
                                <p className="text-xs text-muted-foreground mt-1">
                                    Click for details
                                </p>
                            )}
                        </TooltipContent>
                    </Tooltip>
                </TooltipProvider>

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
