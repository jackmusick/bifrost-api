import {
	createElement,
	type ComponentType,
	useEffect,
	useMemo,
	useRef,
	useState,
} from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { ListPageHeader } from "@/components/layout/ListPageHeader";
import { Button } from "@/components/ui/button";
import { WorkflowKeys } from "@/pages/settings/WorkflowKeys";
import { Branding } from "@/pages/settings/Branding";
import { OAuth } from "@/pages/settings/OAuth";
import { GitHub } from "@/pages/settings/GitHub";
import { AIModelSettings } from "@/pages/settings/AIModelSettings";
import { AIEmbeddingSettings } from "@/pages/settings/AIEmbeddingSettings";
import { AIBehaviorSettings } from "@/pages/settings/AIBehaviorSettings";
import { AIUsageSettings } from "@/pages/settings/AIUsageSettings";
import { MemorySettings } from "@/pages/settings/MemorySettings";
import { RequiredInstructionsSettings } from "@/pages/settings/RequiredInstructionsSettings";
import { MCP } from "@/pages/settings/MCP";
import { Maintenance } from "@/pages/settings/Maintenance";
import { cn } from "@/lib/utils";
import {
	Bot,
	BrainCircuit,
	ChevronDown,
	Database,
	DollarSign,
	Key,
	Layers3,
	MessageSquareText,
	Palette,
	Plug,
	ScrollText,
	Shield,
	Wrench,
	type LucideIcon,
} from "lucide-react";
import { Github } from "@/components/icons/GithubIcon";

type SettingsItem = {
	value: string;
	label: string;
	icon: ComponentType<{ className?: string }>;
	content: ComponentType;
};

type SettingsSection = {
	id: string;
	label: string;
	icon: LucideIcon;
	items: SettingsItem[];
};

const settingsSections: SettingsSection[] = [
	{
		id: "ai",
		label: "AI",
		icon: Bot,
		items: [
			{
				value: "ai",
				label: "Models",
				icon: Layers3,
				content: AIModelSettings,
			},
			{
				value: "ai-embeddings",
				label: "Embeddings",
				icon: Database,
				content: AIEmbeddingSettings,
			},
			{
				value: "ai-chat",
				label: "Chat Instructions",
				icon: MessageSquareText,
				content: AIBehaviorSettings,
			},
			{
				value: "ai-memory",
				label: "Memory",
				icon: BrainCircuit,
				content: MemorySettings,
			},
			{
				value: "ai-instructions",
				label: "Default MCP Instructions",
				icon: ScrollText,
				content: RequiredInstructionsSettings,
			},
			{
				value: "ai-usage",
				label: "Usage & Pricing",
				icon: DollarSign,
				content: AIUsageSettings,
			},
		],
	},
	{
		id: "connections",
		label: "Connections",
		icon: Plug,
		items: [
			{ value: "mcp", label: "MCP", icon: Plug, content: MCP },
			{ value: "github", label: "GitHub", icon: Github, content: GitHub },
		],
	},
	{
		id: "security",
		label: "Security",
		icon: Shield,
		items: [
			{
				value: "sso",
				label: "Authentication",
				icon: Shield,
				content: OAuth,
			},
			{
				value: "workflow-keys",
				label: "Workflow Keys",
				icon: Key,
				content: WorkflowKeys,
			},
		],
	},
	{
		id: "platform",
		label: "Platform",
		icon: Palette,
		items: [
			{
				value: "branding",
				label: "Branding",
				icon: Palette,
				content: Branding,
			},
			{
				value: "maintenance",
				label: "Maintenance",
				icon: Wrench,
				content: Maintenance,
			},
		],
	},
];

function findActiveSectionId(currentTab: string) {
	return (
		settingsSections.find((section) =>
			section.items.some((item) => item.value === currentTab),
		)?.id ?? settingsSections[0].id
	);
}

export function Settings() {
	const navigate = useNavigate();
	const location = useLocation();

	// Parse the current tab from the URL path
	const requestedTab = location.pathname.split("/settings/")[1];
	const currentTab = settingsSections.some((section) =>
		section.items.some((item) => item.value === requestedTab),
	)
		? requestedTab
		: "ai";
	const activeSectionId = findActiveSectionId(currentTab);
	const [expandedSections, setExpandedSections] = useState<string[]>(() => [
		activeSectionId,
	]);
	const [visitedTabs, setVisitedTabs] = useState(() => new Set([currentTab]));
	const [previousTab, setPreviousTab] = useState(currentTab);
	if (previousTab !== currentTab) {
		setPreviousTab(currentTab);
		setVisitedTabs((tabs) => new Set([...tabs, currentTab]));
		setExpandedSections((sections) =>
			sections.includes(activeSectionId)
				? sections
				: [...sections, activeSectionId],
		);
	}
	const contentRef = useRef<HTMLElement>(null);
	const mobileNavigationRef = useRef<HTMLButtonElement>(null);
	const [mobileNavigationOpen, setMobileNavigationOpen] = useState(false);
	const activeLabel =
		settingsSections
			.flatMap((section) => section.items)
			.find((item) => item.value === currentTab)?.label ?? "Models";

	const sectionState = useMemo(
		() => new Set(expandedSections),
		[expandedSections],
	);

	const handleRouteChange = (value: string) => {
		const destinationSection = findActiveSectionId(value);
		setExpandedSections((sections) =>
			sections.includes(destinationSection)
				? sections
				: [...sections, destinationSection],
		);
		if (mobileNavigationOpen) mobileNavigationRef.current?.focus();
		setMobileNavigationOpen(false);
		navigate(`/settings/${value}`);
	};

	const toggleSection = (sectionId: string) => {
		setExpandedSections((sections) =>
			sections.includes(sectionId)
				? sections.filter((id) => id !== sectionId)
				: [...sections, sectionId],
		);
	};

	// Redirect /settings to /settings/ai (first tab)
	useEffect(() => {
		if (requestedTab !== currentTab) {
			navigate(`/settings/${currentTab}`, { replace: true });
		}
	}, [requestedTab, currentTab, navigate]);

	useEffect(() => {
		if (contentRef.current) contentRef.current.scrollTop = 0;
	}, [currentTab]);

	return (
		<div className="mx-auto flex min-w-0 w-full max-w-7xl flex-col gap-6 lg:h-full lg:min-h-0">
			<ListPageHeader
				title="Settings"
				description="Manage platform settings and configuration"
			/>
			<Button
				variant="outline"
				className="h-auto min-h-11 w-full justify-between gap-3 whitespace-normal px-4 py-3 text-left lg:hidden"
				aria-label={`Settings navigation: ${activeLabel}`}
				aria-expanded={mobileNavigationOpen}
				ref={mobileNavigationRef}
				aria-controls="settings-navigation"
				onClick={() => setMobileNavigationOpen((open) => !open)}
			>
				<span className="min-w-0 space-y-1 [overflow-wrap:anywhere]">
					<span className="block text-xs font-normal text-muted-foreground">
						Settings navigation
					</span>
					<span className="block">{activeLabel}</span>
				</span>
				<ChevronDown
					className={cn(
						"size-4 shrink-0 transition-transform duration-[var(--bf-motion-disclosure)] motion-reduce:transition-none",
						mobileNavigationOpen && "rotate-180",
					)}
				/>
			</Button>

			<div className="grid gap-4 lg:min-h-0 lg:flex-1 lg:gap-6 lg:grid-cols-[16rem_minmax(0,1fr)]">
				<nav
					id="settings-navigation"
					aria-label="Settings sections"
					className={cn(
						"min-h-0 rounded-[var(--bf-radius-surface)] border bg-card p-2 lg:block lg:overflow-auto",
						!mobileNavigationOpen && "hidden",
					)}
				>
					{settingsSections.map((section) => {
						const SectionIcon = section.icon;
						const isExpanded = sectionState.has(section.id);
						const containsActive = section.id === activeSectionId;

						return (
							<div key={section.id} className="space-y-1">
								<button
									type="button"
									aria-expanded={isExpanded}
									aria-controls={`settings-section-${section.id}`}
									onClick={() => toggleSection(section.id)}
									className={cn(
										"flex min-h-11 w-full items-center gap-2 rounded-[var(--bf-radius-control)] px-3 py-2 text-left text-sm font-medium transition-colors duration-[var(--bf-motion-feedback)] motion-reduce:transition-none hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
										containsActive && "text-foreground",
										!containsActive &&
											"text-muted-foreground",
									)}
								>
									<SectionIcon className="h-4 w-4 shrink-0" />
									<span className="flex-1">
										{section.label}
									</span>
									<ChevronDown
										className={cn(
											"h-4 w-4 shrink-0 transition-transform duration-[var(--bf-motion-disclosure)] motion-reduce:transition-none",
											!isExpanded && "-rotate-90",
										)}
										aria-hidden="true"
									/>
								</button>

								{isExpanded && (
									<div
										id={`settings-section-${section.id}`}
										className="space-y-1 pb-2 pl-3"
									>
										{section.items.map((item) => {
											const ItemIcon = item.icon;
											const isActive =
												item.value === currentTab;

											return (
												<button
													key={item.value}
													type="button"
													aria-current={
														isActive
															? "page"
															: undefined
													}
													onClick={() =>
														handleRouteChange(
															item.value,
														)
													}
													className={cn(
														"flex min-h-11 w-full items-center gap-2 rounded-[var(--bf-radius-control)] px-3 py-2 text-left text-sm transition-colors duration-[var(--bf-motion-feedback)] motion-reduce:transition-none hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
														isActive
															? "bg-primary/10 font-medium text-primary"
															: "text-muted-foreground",
													)}
												>
													<ItemIcon className="h-4 w-4 shrink-0" />
													<span>{item.label}</span>
												</button>
											);
										})}
									</div>
								)}
							</div>
						);
					})}
				</nav>

				<section
					ref={contentRef}
					className="min-w-0 pb-6 lg:min-h-0 lg:overflow-auto lg:px-1 lg:pr-3"
				>
					{settingsSections
						.flatMap((section) => section.items)
						.filter((item) => visitedTabs.has(item.value))
						.map((item) => (
							<div
								key={item.value}
								hidden={item.value !== currentTab}
							>
								{createElement(item.content)}
							</div>
						))}
				</section>
			</div>
		</div>
	);
}
