import { useEffect, useRef, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ListPageHeader } from "@/components/layout/ListPageHeader";
import {
	PageScrollArea,
	PageWorkspace,
} from "@/components/layout/PageWorkspace";
import { BasicInfo } from "@/pages/user-settings/BasicInfo";
import { Security } from "@/pages/user-settings/Security";
import { DeveloperSettings } from "@/pages/user-settings/Developer";
import { UserMCPConnections } from "@/components/user/UserMCPConnections";
import { Preferences } from "@/pages/user-settings/Preferences";

const settingsTabs = [
	{ value: "basic-info", label: "Basic Info", Component: BasicInfo },
	{ value: "security", label: "Security", Component: Security },
	{
		value: "connections",
		label: "Connections",
		Component: UserMCPConnections,
	},
	{ value: "preferences", label: "Preferences", Component: Preferences },
	{ value: "developer", label: "Developer", Component: DeveloperSettings },
];

export function UserSettings() {
	const navigate = useNavigate();
	const location = useLocation();
	const tabStripRef = useRef<HTMLDivElement>(null);

	const requestedTab = location.pathname.split("/user-settings/")[1];
	const currentTab = settingsTabs.some((tab) => tab.value === requestedTab)
		? requestedTab
		: "basic-info";
	const [visited, setVisited] = useState(() => new Set([currentTab]));
	if (!visited.has(currentTab)) setVisited(new Set([...visited, currentTab]));

	useEffect(() => {
		const strip = tabStripRef.current;
		const active = strip?.querySelector<HTMLElement>(
			'[aria-selected="true"]',
		);
		if (!strip || !active) return;
		const container = strip.getBoundingClientRect();
		const selected = active.getBoundingClientRect();
		if (selected.right > container.right)
			strip.scrollLeft += selected.right - container.right;
		else if (selected.left < container.left)
			strip.scrollLeft -= container.left - selected.left;
	}, [currentTab]);

	const handleTabChange = (value: string) => {
		navigate(`/user-settings/${value}`);
	};

	// Redirect /user-settings to /user-settings/basic-info
	useEffect(() => {
		if (requestedTab !== currentTab) {
			navigate("/user-settings/basic-info", { replace: true });
		}
	}, [requestedTab, currentTab, navigate]);

	return (
		<PageWorkspace className="max-w-3xl mx-auto">
			<ListPageHeader
				title="User Settings"
				description="Manage your profile, security, connections, and preferences"
			/>

			<Tabs
				value={currentTab}
				onValueChange={handleTabChange}
				className="flex min-h-0 flex-1 flex-col"
			>
				<div ref={tabStripRef} className="overflow-x-auto">
					<TabsList variant="line" className="h-auto w-max">
						{settingsTabs.map(({ value, label }) => (
							<TabsTrigger
								key={value}
								className="min-h-11"
								value={value}
							>
								{label}
							</TabsTrigger>
						))}
					</TabsList>
				</div>

				{settingsTabs
					.filter(({ value }) => visited.has(value))
					.map(({ value, Component }) => (
						<TabsContent
							key={value}
							value={value}
							forceMount
							hidden={value !== currentTab}
							className="mt-6 flex min-h-0 flex-1 flex-col data-[state=inactive]:hidden"
						>
							<PageScrollArea>
								<Component />
							</PageScrollArea>
						</TabsContent>
					))}
			</Tabs>
		</PageWorkspace>
	);
}
