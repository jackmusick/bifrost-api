import {
    ChevronDown,
    LogOut,
    Settings,
    User,
    Circle,
    RefreshCw,
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

export function Header() {
    const navigate = useNavigate();
    const { user } = useAuth();
    const scope = useScopeStore((state) => state.scope);
    const setScope = useScopeStore((state) => state.setScope);
    const isGlobalScope = useScopeStore((state) => state.isGlobalScope);
    const { data: organizations, isLoading: orgsLoading } = useOrganizations();
    const {
        data: engineHealth,
        isLoading: healthLoading,
        refetch,
        isRefetching,
    } = useWorkflowEngineHealth();

    const userEmail = user?.userDetails || "Loading...";
    const userName = user?.userDetails?.split("@")[0] || "User";

    // Check if user is platform admin
    const isPlatformAdmin = user?.userDetails === "jack@gocovi.com"; // TODO: Get from user profile

    // Determine status color and message
    const getServerStatus = () => {
        if (healthLoading || isRefetching) {
            return {
                color: "text-yellow-500",
                status: "checking",
                message: "Checking server status...",
                canClick: false,
            };
        }

        if (engineHealth?.status === "healthy") {
            return {
                color: "text-green-500",
                status: "healthy",
                message: "Server is healthy",
                canClick: true,
            };
        }

        return {
            color: "text-red-500",
            status: "unhealthy",
            message: "Server is unavailable",
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
        <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <div className="flex h-16 items-center px-6 lg:px-8">
                {/* Logo */}
                <div className="flex items-center gap-2 font-semibold">
                    <img src="/logo.svg" alt="Bifrost" className="h-8 w-8" />
                    <span className="hidden sm:inline-block">
                        Bifrost Integrations
                    </span>
                </div>

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
