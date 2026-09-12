import { NavLink } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { cn } from "@/lib/utils";

/** Route links preserve browser navigation and the existing protected dashboard. */
export function WorkspaceTabs() {
	const { isPlatformAdmin } = useAuth();
	if (!isPlatformAdmin) return null;
	return (
		<nav aria-label="Workspace views" className="flex items-center gap-1">
			{[
				{ to: "/", label: "Home" },
				{ to: "/dashboard", label: "Dashboard" },
			].map(({ to, label }) => (
				<NavLink
					key={to}
					to={to}
					end
					className={({ isActive }) =>
						cn(
							"inline-flex min-h-11 items-center border-b-2 px-3 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-ring",
							isActive
								? "border-primary text-primary"
								: "border-transparent text-muted-foreground hover:text-foreground",
						)
					}
				>
					{label}
				</NavLink>
			))}
		</nav>
	);
}
