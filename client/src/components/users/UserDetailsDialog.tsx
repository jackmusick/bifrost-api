import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useUserRoles, useUserForms } from "@/hooks/useUsers";
import { formatDate, formatDateShort } from "@/lib/utils";
import type { components } from "@/lib/v1";
import {
	AlertCircle,
	UserCog,
	FileCode,
	Shield,
	Clock,
	X,
} from "lucide-react";
type User = components["schemas"]["UserPublic"];
type UserRolesResponse = components["schemas"]["UserRolesResponse"];
type UserFormsResponse = components["schemas"]["RoleFormsResponse"];

interface UserDetailsDialogProps {
	user?: User | undefined;
	open: boolean;
	onClose: () => void;
}

function ReadErrorState({
	title,
	message,
	onRetry,
	pending,
}: {
	title: string;
	message: string;
	onRetry: () => void;
	pending: boolean;
}) {
	return (
		<div
			role="alert"
			aria-label={title}
			className="rounded-[var(--bf-radius-surface)] border border-[var(--bf-danger)]/20 bg-[var(--bf-danger-soft)] p-4 text-sm text-[var(--bf-danger)]"
		>
			<div className="flex items-start gap-2">
				<AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
				<div className="space-y-1">
					<p className="font-medium">{title}</p>
					<p className="[overflow-wrap:anywhere]">{message}</p>
				</div>
			</div>
			<Button type="button" variant="outline" className="mt-3 min-h-11" disabled={pending} onClick={onRetry}>{pending ? "Retrying…" : "Retry"}</Button>
		</div>
	);
}

export function UserDetailsDialog({
	user,
	open,
	onClose,
}: UserDetailsDialogProps) {
	const { data: roles, isLoading: rolesLoading, error: rolesError, isFetching: rolesFetching, refetch: refetchRoles } =
		useUserRoles(user?.id);
	const { data: formsAccess, isLoading: formsLoading, error: formsError, isFetching: formsFetching, refetch: refetchForms } =
		useUserForms(user?.id);

	if (!user) return null;

	return (
		<Dialog open={open} onOpenChange={onClose}>
			<DialogContent
				showCloseButton={false}
				className="flex h-[100dvh] w-full max-w-none flex-col gap-0 overflow-hidden rounded-none border-border/70 p-0 shadow-xl motion-reduce:transition-none motion-reduce:animate-none sm:h-auto sm:max-h-[min(90vh,48rem)] sm:w-[min(92vw,700px)] sm:rounded-[var(--bf-radius-feature)]"
			>
				<DialogHeader className="shrink-0 border-b border-border/70 px-4 pb-4 pt-[max(1rem,env(safe-area-inset-top))] text-left sm:px-6">
					<div className="flex items-start gap-3">
						<div className="min-w-0 flex-1">
							<DialogTitle className="text-pretty [overflow-wrap:anywhere]">
								{user.name || user.email}
							</DialogTitle>
							<DialogDescription className="mt-1.5 text-sm leading-5 [overflow-wrap:anywhere]">
								{user.email} •{" "}
								{user.is_superuser
									? "MSP Technician"
									: "Organization User"}
							</DialogDescription>
						</div>
						<Button
							type="button"
							variant="ghost"
							size="icon-lg"
							onClick={onClose}
							aria-label="Close dialog"
							className="h-11 w-11 shrink-0 rounded-[var(--bf-radius-control)] border border-border/70 bg-background/90 text-foreground hover:bg-muted motion-reduce:transition-none"
						>
							<X className="h-5 w-5" />
						</Button>
					</div>
				</DialogHeader>

				<div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4 sm:px-6">
					{/* User Info Card */}
					<Card>
						<CardHeader>
							<CardTitle className="text-base">
								User Information
							</CardTitle>
						</CardHeader>
						<CardContent className="space-y-3">
							<div className="flex items-center justify-between">
								<span className="text-sm text-muted-foreground">
									User Type
								</span>
								<Badge
									variant={
										user.is_superuser
											? "default"
											: "secondary"
									}
								>
									{user.is_superuser ? (
										<>
											<Shield className="mr-1 h-3 w-3" />
											Platform Admin
										</>
									) : (
										"Organization User"
									)}
								</Badge>
							</div>

							<div className="flex items-center justify-between">
								<span className="text-sm text-muted-foreground">
									Status
								</span>
								<Badge
									variant="outline"
									className={
										user.is_active
											? "border-emerald-500/20 bg-emerald-500/10 text-emerald-700 dark:bg-emerald-400/15 dark:text-emerald-300"
											: "border-border/70 bg-muted/50 text-muted-foreground"
									}
								>
									{user.is_active ? "Active" : "Inactive"}
								</Badge>
							</div>

							<div className="flex items-center justify-between">
								<span className="text-sm text-muted-foreground">
									Last Login
								</span>
								<span className="text-sm flex items-center gap-1">
									<Clock className="h-3 w-3" />
									{user.last_login
										? formatDate(user.last_login)
										: "Never logged in"}
								</span>
							</div>

							<div className="flex items-center justify-between">
								<span className="text-sm text-muted-foreground">
									Created
								</span>
								<span className="text-sm">
									{user.created_at
										? formatDateShort(user.created_at)
										: "N/A"}
								</span>
							</div>
						</CardContent>
					</Card>

					{/* Roles and Forms Tabs (only for org users - non-superusers with org) */}
					{!user.is_superuser && user.organization_id && (
						<Tabs defaultValue="roles">
							<TabsList className="grid min-h-14 w-full grid-cols-2">
								<TabsTrigger value="roles" className="min-h-11">
									<UserCog className="mr-2 h-4 w-4" />
									Roles
								</TabsTrigger>
								<TabsTrigger value="forms" className="min-h-11">
									<FileCode className="mr-2 h-4 w-4" />
									Form Access
								</TabsTrigger>
							</TabsList>

							<TabsContent value="roles" className="mt-4">
								<Card>
									<CardHeader>
										<CardTitle className="text-base">
											Assigned Roles
										</CardTitle>
										<CardDescription>
											Roles determine which forms this
											user can access
										</CardDescription>
									</CardHeader>
									<CardContent>
										{rolesError ? (
											<ReadErrorState
												title="Unable to load roles"
												onRetry={() => { void refetchRoles(); }}
												pending={rolesFetching}
												message={
													rolesError instanceof Error
														? rolesError.message
														: "The assigned roles could not be loaded."
												}
											/>
										) : rolesLoading ? (
											<div className="space-y-2">
												{[...Array(2)].map((_, i) => (
													<Skeleton
														key={i}
														className="h-10 w-full"
													/>
												))}
											</div>
										) : roles &&
										  (roles as UserRolesResponse)
												.role_ids &&
										  (roles as UserRolesResponse).role_ids
												.length > 0 ? (
											<div className="space-y-2">
												{(
													roles as UserRolesResponse
												).role_ids.map(
													(roleId: string) => (
														<div
															key={roleId}
															className="flex items-center justify-between rounded-lg bg-muted/50 p-3 ring-1 ring-foreground/5"
														>
															<div>
																<p className="font-medium">
																	{roleId}
																</p>
																<p className="text-sm text-muted-foreground">
																	Role ID:{" "}
																	{roleId}
																</p>
															</div>
														</div>
													),
												)}
											</div>
										) : (
											<div className="flex flex-col items-center justify-center py-8 text-center">
												<UserCog className="h-12 w-12 text-muted-foreground" />
												<p className="mt-2 text-sm text-muted-foreground">
													No roles assigned to this
													user
												</p>
											</div>
										)}
									</CardContent>
								</Card>
							</TabsContent>

							<TabsContent value="forms" className="mt-4">
								<Card>
									<CardHeader>
										<CardTitle className="text-base">
											Form Access
										</CardTitle>
										<CardDescription>
											Forms this user can execute based on
											their roles
										</CardDescription>
									</CardHeader>
									<CardContent>
										{formsError ? (
											<ReadErrorState
												title="Unable to load form access"
												onRetry={() => { void refetchForms(); }}
												pending={formsFetching}
												message={
													formsError instanceof Error
														? formsError.message
														: "The accessible forms could not be loaded."
												}
											/>
										) : formsLoading ? (
											<div className="space-y-2">
												{[...Array(2)].map((_, i) => (
													<Skeleton
														key={i}
														className="h-10 w-full"
													/>
												))}
											</div>
										) : formsAccess &&
										  (formsAccess as UserFormsResponse)
												.form_ids ? (
											(formsAccess as UserFormsResponse)
												.form_ids.length > 0 ? (
												<div className="space-y-2">
													{(
														formsAccess as UserFormsResponse
													).form_ids.map(
														(formId: string) => (
															<div
																key={formId}
																className="rounded-lg bg-muted/50 p-3 ring-1 ring-foreground/5"
															>
																<p className="font-medium">
																	{formId}
																</p>
															</div>
														),
													)}
												</div>
											) : (
												<div className="flex flex-col items-center justify-center py-8 text-center">
													<FileCode className="h-12 w-12 text-muted-foreground" />
													<p className="mt-2 text-sm text-muted-foreground">
														No forms accessible to
														this user
													</p>
												</div>
											)
										) : null}
									</CardContent>
								</Card>
							</TabsContent>
						</Tabs>
					)}

					{/* Platform admins have full access */}
					{user.is_superuser && (
						<Card>
							<CardHeader>
								<CardTitle className="text-base">
									Access Level
								</CardTitle>
							</CardHeader>
							<CardContent>
								<div className="rounded-lg border border-sky-500/20 bg-sky-500/10 p-4 text-sky-900 dark:text-sky-200">
									<p className="text-sm font-medium">
										Full Platform Access
									</p>
									<p className="text-sm">
										{user.is_superuser
											? "MSP Admin - Full access to all platform features"
											: "MSP Technician - Access to manage workflows and configurations"}
									</p>
								</div>
							</CardContent>
						</Card>
					)}
				</div>
			</DialogContent>
		</Dialog>
	);
}
