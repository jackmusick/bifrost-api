import { useQuery } from "@tanstack/react-query";
import { FlaskConical, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { SolutionManagedBadge } from "@/components/solutions/SolutionManagedBadge";
import { effectiveAccess } from "@/services/filePolicies";
import { InlineLoader } from "./InlineLoader";

interface EffectiveAccessPanelProps {
	location: string;
	scope: string | null;
	path: string | null;
	readOnly?: boolean;
	managedBySolution?: boolean;
	solutionId?: string | null;
	onOpenTest: () => void;
	onManagePolicy: () => void;
}

export function EffectiveAccessPanel({
	location,
	scope,
	path,
	readOnly = false,
	managedBySolution = false,
	solutionId = null,
	onOpenTest,
	onManagePolicy,
}: EffectiveAccessPanelProps) {
	const accessQuery = useQuery({
		queryKey: ["effective-access", location, scope, path],
		queryFn: () => effectiveAccess(location, path ?? "", scope),
		enabled: path !== null,
		retry: false,
	});
	const policies = accessQuery.data ?? [];
	const error = accessQuery.isError;
	const loading = accessQuery.isLoading || accessQuery.isFetching;
	const formatPath = (policyPath: string) =>
		policyPath
			? policyPath.startsWith("/")
				? policyPath
				: `/${policyPath}`
			: "/";
	const formatSource = (policyPath: string) =>
		policyPath
			? `Inherited From ${formatPath(policyPath)}`
			: "Inherited From Share Root";

	return (
		<section
			aria-label="Effective access"
			className="flex h-full min-h-0 min-w-0 flex-col"
		>
			<div className="flex shrink-0 flex-col gap-3 border-b px-3 py-3">
				<div className="flex min-w-0 flex-wrap items-center gap-2 text-sm font-semibold">
					<ShieldCheck className="size-4 text-primary" />
					<h2 className="min-w-0 leading-5">Effective Access</h2>
					{managedBySolution && (
						<SolutionManagedBadge
							solutionId={solutionId ?? undefined}
						/>
					)}
				</div>
				<div className="flex flex-wrap gap-2">
					{!readOnly && (
						<Button
							type="button"
							variant="outline"
							size="default"
							className="min-h-11"
							disabled={path === null}
							onClick={onManagePolicy}
						>
							<ShieldCheck className="size-4" />
							Manage Policy
						</Button>
					)}
					<Button
						type="button"
						size="default"
						className="min-h-11"
						onClick={onOpenTest}
						disabled={path === null}
					>
						<FlaskConical className="size-4" />
						Test Access
					</Button>
				</div>
			</div>
			<div className="min-h-0 min-w-0 flex-1 overflow-auto p-3 text-sm">
				{path === null && (
					<p className="[overflow-wrap:anywhere] text-muted-foreground">
						Select an item to see what governs it.
					</p>
				)}
				{loading && <InlineLoader label="Resolving…" />}
				{error && (
					<div role="alert" className="space-y-2">
						<p className="[overflow-wrap:anywhere] text-destructive">
							Couldn’t resolve access for this item.
						</p>
						<Button
							type="button"
							variant="outline"
							size="default"
							className="min-h-11"
							disabled={accessQuery.isFetching}
							onClick={() => void accessQuery.refetch()}
						>
							Retry access
						</Button>
					</div>
				)}
				{path !== null &&
					!loading &&
					!error &&
					policies.length === 0 && (
						<p className="[overflow-wrap:anywhere] text-muted-foreground">
							No policy governs this path (default deny).
						</p>
					)}
				<ul className="space-y-2">
					{policies.map((policy, index) => (
						<li
							key={
								policy.id ?? `${policy.location}:${policy.path}`
							}
							className="border-b pb-3 last:border-b-0 last:pb-0"
						>
							<div className="flex flex-wrap items-center gap-2">
								<Badge
									variant={
										index === 0 ? "secondary" : "outline"
									}
								>
									{index === 0
										? "Winning Policy"
										: formatSource(policy.path)}
								</Badge>
								<span className="min-w-0 [overflow-wrap:anywhere] font-mono text-xs text-muted-foreground">
									{policy.location}
									{formatPath(policy.path)}
								</span>
							</div>
							{policy.policies.policies.length === 0 ? (
								<p className="mt-2 text-xs text-muted-foreground">
									No rules
								</p>
							) : (
								<ul className="mt-2 space-y-1">
									{policy.policies.policies.map((rule, i) =>
										"$ref" in rule ? (
											<li
												key={rule.$ref}
												className="[overflow-wrap:anywhere] text-muted-foreground"
											>
												<span className="[overflow-wrap:anywhere] font-mono font-medium text-foreground">
													ref: {rule.$ref}
												</span>
											</li>
										) : (
											<li
												key={rule.name ?? i}
												className="[overflow-wrap:anywhere] text-muted-foreground"
											>
												<span className="[overflow-wrap:anywhere] font-medium text-foreground">
													{rule.name}
												</span>{" "}
												<span className="[overflow-wrap:anywhere]">
													- {rule.actions.join(", ")}
												</span>
											</li>
										),
									)}
								</ul>
							)}
						</li>
					))}
				</ul>
			</div>
		</section>
	);
}
