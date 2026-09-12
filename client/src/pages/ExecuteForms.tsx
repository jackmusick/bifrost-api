import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, FileCode, PlayCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useForms } from "@/hooks/useForms";
import { useAuth } from "@/contexts/AuthContext";
import { getErrorMessage } from "@/lib/api-error";

function ExecuteFormsReadError({
	cached,
	error,
	retrying,
	onRetry,
}: {
	cached: boolean;
	error: unknown;
	retrying: boolean;
	onRetry: () => void;
}) {
	return (
		<div
			role="alert"
			className="space-y-3 [overflow-wrap:anywhere] rounded-[var(--bf-radius-surface)] border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive"
		>
			<div className="flex items-start gap-3">
				<AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
				<div className="min-w-0 space-y-1">
					<p className="font-medium">
						Could not {cached ? "refresh" : "load"} forms
					</p>
					<p className="text-destructive/90">
						{cached
							? `Previously loaded forms are still shown. ${getErrorMessage(error, "Try loading the forms again.")}`
							: getErrorMessage(
									error,
									"Try loading the forms again.",
								)}
					</p>
				</div>
			</div>
			<Button
				variant="outline"
				className="min-h-11"
				disabled={retrying}
				onClick={onRetry}
			>
				{retrying ? "Retrying…" : "Retry loading"}
			</Button>
		</div>
	);
}

export function ExecuteForms() {
	const navigate = useNavigate();
	const { isPlatformAdmin } = useAuth();
	const {
		data: forms,
		isLoading,
		isError,
		error,
		isFetching,
		refetch,
	} = useForms();

	const activeForms = useMemo(() => {
		return forms?.filter((form) => form.is_active) || [];
	}, [forms]);

	const formValidation = useMemo(() => {
		const validationMap = new Map<
			string,
			{ valid: boolean; missingParams: string[] }
		>();

		activeForms.forEach((form) => {
			const formWithParams = form as typeof form & {
				missing_required_params?: string[];
			};
			const missingParams = formWithParams.missing_required_params || [];
			validationMap.set(form.id, {
				valid: missingParams.length === 0,
				missingParams,
			});
		});

		return validationMap;
	}, [activeForms]);

	const visibleForms = useMemo(() => {
		if (isPlatformAdmin) {
			return activeForms;
		}

		return activeForms.filter((form) => {
			const validation = formValidation.get(form.id);
			return validation?.valid !== false;
		});
	}, [activeForms, formValidation, isPlatformAdmin]);

	const handleExecute = (formId: string) => {
		navigate(`/execute/${formId}`);
	};

	const cachedForms = forms !== undefined;
	const readError = isError
		? {
				cached: cachedForms,
				error,
				retrying: isFetching,
			}
		: null;

	return (
		<div className="mx-auto w-full min-w-0 max-w-6xl space-y-6">
			<div>
				<h1 className="font-display text-2xl font-semibold tracking-tight sm:text-3xl">
					Execute Forms
				</h1>
				<p className="mt-2 text-muted-foreground">
					Select a form to execute a workflow with a guided interface
				</p>
			</div>

			{isLoading ? (
				<div className="grid grid-cols-1 gap-3 sm:grid-cols-[repeat(auto-fill,minmax(min(100%,280px),1fr))]">
					{[...Array(6)].map((_, i) => (
						<Skeleton key={i} className="h-48 w-full" />
					))}
				</div>
			) : readError && !cachedForms ? (
				<ExecuteFormsReadError
					{...readError}
					onRetry={() => void refetch()}
				/>
			) : (
				<>
					{readError && cachedForms && (
						<ExecuteFormsReadError
							{...readError}
							onRetry={() => void refetch()}
						/>
					)}
					{visibleForms.length > 0 ? (
						<div className="grid grid-cols-1 gap-3 sm:grid-cols-[repeat(auto-fill,minmax(min(100%,280px),1fr))]">
							{visibleForms.map((form) => {
								const validation = formValidation.get(form.id);
								const fieldCount =
									(
										form.form_schema as {
											fields?: unknown[];
										} | null
									)?.fields?.length || 0;

								return (
									<Card
										key={form.id}
										className="min-w-0 hover:border-primary transition-colors"
									>
										<CardHeader className="min-w-0 space-y-3">
											<div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
												<CardTitle className="min-w-0 text-lg font-semibold tracking-tight sm:text-xl">
													<span className="block [overflow-wrap:anywhere]">
														{form.name}
													</span>
												</CardTitle>
												<div className="flex max-w-full flex-wrap items-start gap-2">
													{form.organization_id ===
														null && (
														<Badge
															variant="secondary"
															className="shrink-0"
														>
															Global
														</Badge>
													)}
													{!validation?.valid && (
														<Badge
															variant="destructive"
															className="h-auto max-w-full items-start whitespace-normal break-all py-1 text-left leading-tight"
														>
															<AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" />
															Invalid
														</Badge>
													)}
												</div>
											</div>
											{form.description && (
												<CardDescription className="[overflow-wrap:anywhere]">
													{form.description}
												</CardDescription>
											)}
										</CardHeader>
										<CardContent className="min-w-0 space-y-4">
											<div className="min-w-0">
												<p className="text-sm font-medium text-muted-foreground">
													Workflow
												</p>
												<p className="mt-1 font-mono text-sm [overflow-wrap:anywhere]">
													{form.workflow_id ||
														"No workflow linked"}
												</p>
											</div>
											<div className="min-w-0">
												<p className="text-sm font-medium text-muted-foreground">
													Fields
												</p>
												<p className="mt-1 text-sm">
													{fieldCount} field
													{fieldCount === 1
														? ""
														: "s"}
												</p>
											</div>
											{!validation?.valid &&
											validation?.missingParams.length ? (
												<div className="min-w-0 border-t pt-2">
													<span className="text-sm font-medium text-destructive">
														Missing required
														parameters:
													</span>
													<div className="mt-2 flex min-w-0 flex-wrap gap-1">
														{validation.missingParams.map(
															(param) => (
																<Badge
																	key={param}
																	variant="outline"
																	className="h-auto max-w-full whitespace-normal break-all py-1 text-xs font-mono leading-tight"
																>
																	{param}
																</Badge>
															),
														)}
													</div>
												</div>
											) : null}
											<Button
												className="w-full"
												onClick={() =>
													handleExecute(form.id)
												}
												disabled={!validation?.valid}
												title={
													!validation?.valid
														? `Cannot execute: Missing required parameters (${validation?.missingParams.join(", ")})`
														: "Execute workflow"
												}
											>
												<PlayCircle className="mr-2 h-4 w-4" />
												Execute Workflow
											</Button>
										</CardContent>
									</Card>
								);
							})}
						</div>
					) : (
						<Card>
							<CardContent className="flex flex-col items-center justify-center py-12 text-center">
								<FileCode className="h-12 w-12 text-muted-foreground" />
								<h3 className="mt-4 text-lg font-semibold">
									No active forms available
								</h3>
								<p className="mt-2 text-sm text-muted-foreground">
									Contact your administrator to create and
									activate forms
								</p>
							</CardContent>
						</Card>
					)}
				</>
			)}
		</div>
	);
}
