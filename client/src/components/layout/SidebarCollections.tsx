import { Folder, Plus } from "lucide-react";
import { useLocation } from "react-router-dom";
import { $api } from "@/lib/api-client";
import { getIcon } from "@/lib/icons";
import { SidebarLink } from "./sidebarLinks";

export function SidebarCollections({
	isCollapsed,
	onNavigate,
}: {
	isCollapsed: boolean;
	onNavigate?: () => void;
}) {
	const location = useLocation();
	const home = $api.useQuery("get", "/api/home");
	const collections = home.data?.collections ?? [];
	const selectedCollection = new URLSearchParams(location.search).get(
		"collection",
	);

	return (
		<div className="space-y-1">
			{collections.map((collection) => {
				const Icon = getIcon(collection.icon, Folder);
				const to = {
					pathname: "/",
					search: `?collection=${encodeURIComponent(collection.id)}`,
				};
				return (
					<SidebarLink
						key={collection.id}
						to={to}
						label={collection.name}
						icon={Icon}
						isCollapsed={isCollapsed}
						onClick={onNavigate}
						isActive={
							location.pathname === "/" &&
							selectedCollection === collection.id
						}
					>
						<span className="min-w-0 truncate">
							{collection.name}
						</span>
					</SidebarLink>
				);
			})}
			<SidebarLink
				to={{ pathname: "/", search: "?newCollection=1" }}
				label="New collection"
				icon={Plus}
				isCollapsed={isCollapsed}
				onClick={onNavigate}
				isActive={
					location.pathname === "/" &&
					new URLSearchParams(location.search).get(
						"newCollection",
					) === "1"
				}
			/>
		</div>
	);
}
