import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Combobox } from "@/components/ui/combobox";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { useUsersFiltered } from "@/hooks/useUsers";
import { testAllActions, type FilePolicyAction } from "@/services/filePolicies";
import { InlineLoader } from "./InlineLoader";

interface TestAccessModalProps {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	location: string;
	scope: string | null;
	path: string;
}

const ACTIONS: FilePolicyAction[] = ["read", "write", "delete", "list"];

function TestAccessSession({
	open,
	onOpenChange,
	location,
	scope,
	path,
}: TestAccessModalProps) {
	// This admin tool must include principals outside the share's scope. The
	// backend resolves the selected user's actual organization and roles.
	const usersQuery = useUsersFiltered(undefined);
	const [userId, setUserId] = useState("");
	const options = useMemo(
		() =>
			(usersQuery.data ?? []).map((user) => ({
				value: user.id,
				label: user.name ? `${user.name} (${user.email})` : user.email,
			})),
		[usersQuery.data],
	);
	const access = useQuery({
		queryKey: ["file-access-test", location, scope, path, userId],
		queryFn: () => testAllActions({ location, scope, path, userId }),
		enabled: !!userId,
		retry: false,
		gcTime: 0,
	});
	const results =
		userId && !access.isFetching && !access.isError
			? access.data
			: undefined;

	return (
		<Dialog open={open} onOpenChange={onOpenChange}>
			<DialogContent className="flex max-h-[90dvh] flex-col gap-0 overflow-hidden p-0 sm:max-w-lg [&_[data-slot=dialog-header]]:pr-16">
				<DialogHeader className="shrink-0 border-b p-5">
					<DialogTitle>Test access</DialogTitle>
					<DialogDescription>
						Check what a user can do with this file or folder.
					</DialogDescription>
				</DialogHeader>
				<div className="min-h-0 space-y-5 overflow-y-auto p-5">
					<dl className="grid grid-cols-[max-content_minmax(0,1fr)] gap-x-3 gap-y-2 text-sm">
						<div className="contents">
							<dt className="text-muted-foreground">Share</dt>
							<dd className="font-medium [overflow-wrap:anywhere]">
								{location}
							</dd>
						</div>
						<div className="contents">
							<dt className="text-muted-foreground">Path</dt>
							<dd className="font-mono text-xs [overflow-wrap:anywhere]">
								{path || "Share root"}
							</dd>
						</div>
						<div className="contents">
							<dt className="text-muted-foreground">Scope</dt>
							<dd className="[overflow-wrap:anywhere]">
								{!scope || scope === "global"
									? "Global"
									: scope}
							</dd>
						</div>
					</dl>
					<div className="space-y-2">
						<Label htmlFor="test-access-user">User</Label>
						<Combobox
							id="test-access-user"
							className="min-h-11"
							options={options}
							value={userId}
							onValueChange={setUserId}
							placeholder="Select a user…"
							searchPlaceholder="Search users…"
							emptyText="No matching users."
							isLoading={usersQuery.isLoading}
							disabled={!options.length}
						/>
						{usersQuery.isError && (
							<div role="alert" className="space-y-2 text-sm">
								<p className="text-destructive">
									Couldn’t load users.
									{options.length
										? " Showing the last loaded users."
										: ""}
								</p>
								<Button
									variant="outline"
									className="min-h-11"
									disabled={usersQuery.isFetching}
									onClick={() => void usersQuery.refetch()}
								>
									Retry users
								</Button>
							</div>
						)}
						{!usersQuery.isLoading &&
							!usersQuery.isError &&
							options.length === 0 && (
								<p className="text-sm text-muted-foreground">
									No users are available to test.
								</p>
							)}
					</div>
					{!userId && options.length > 0 && (
						<p className="text-sm text-muted-foreground">
							Select a user to check read, write, delete, and list
							access.
						</p>
					)}
					{!!userId && access.isFetching && (
						<InlineLoader label="Resolving access…" />
					)}
					{!!userId && access.isError && (
						<div role="alert" className="space-y-2 text-sm">
							<p className="text-destructive">
								Couldn’t test access. No access decision was
								returned.
							</p>
							<Button
								variant="outline"
								className="min-h-11"
								disabled={access.isFetching}
								onClick={() => void access.refetch()}
							>
								Retry test
							</Button>
						</div>
					)}
					{results && (
						<ul
							aria-label="Access test results"
							className="space-y-3"
						>
							{ACTIONS.map((action) => {
								const result = results[action];
								return (
									<li
										key={action}
										className="space-y-2 rounded-[var(--bf-radius-surface)] border p-3 text-sm"
									>
										<div className="flex items-center justify-between gap-3">
											<span className="font-medium capitalize">
												{action}
											</span>
											<Badge
												variant={
													result.allowed
														? "secondary"
														: "destructive"
												}
											>
												{result.allowed
													? "Allowed"
													: "Denied"}
											</Badge>
										</div>
										<p className="text-muted-foreground [overflow-wrap:anywhere]">
											{result.allowed
												? (result.matchedRule ??
													result.matchedPolicy ??
													"Access granted by the applicable policy.")
												: (result.denialReason ??
													"No matching rule.")}
										</p>
									</li>
								);
							})}
						</ul>
					)}
				</div>
			</DialogContent>
		</Dialog>
	);
}

export function TestAccessModal(props: TestAccessModalProps) {
	if (!props.open) return null;
	return (
		<TestAccessSession
			key={JSON.stringify([props.location, props.scope, props.path])}
			{...props}
		/>
	);
}
